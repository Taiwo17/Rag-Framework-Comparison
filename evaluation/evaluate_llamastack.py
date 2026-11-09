
import json
import time
import urllib.error
import urllib.request

from pathlib import Path


BASE_URL = "http://localhost:8321"
VECTOR_DB_ID = "llamastack_devops_rag"
MODEL_ID = "ollama/qwen2.5:3b"
TOP_K = 4
TIMEOUT = 420

BASE_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = BASE_DIR / "evaluation" / "questions.json"
OUTPUT_PATH = (
    BASE_DIR / "evaluation" / "results" / "llamastack-results.json"
)


def save_results(results):
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_PATH.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def post_request(endpoint, payload):
    url = f"{BASE_URL}{endpoint}"

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8")
        raise RuntimeError(
            f"HTTP {error.code}: {error_body}"
        ) from error


def retrieve_chunks(question):
    payload = {
        "vector_db_id": VECTOR_DB_ID,
        "query": question,
        "params": {
            "top_k": TOP_K
        }
    }

    result = post_request("/v1/vector-io/query", payload)

    chunks = result.get("chunks", [])
    scores = result.get("scores", [])

    if not chunks:
        raise RuntimeError("No relevant chunks were retrieved.")

    return chunks, scores


def build_context(chunks):
    context_parts = []

    for chunk in chunks:
        metadata = chunk.get("metadata", {})

        source = metadata.get("source", "Unknown source")
        page = metadata.get("page", "Unknown page")
        chunk_id = chunk.get("chunk_id", "Unknown ID")

        context_parts.append(
            f"[Source: {source}, Page: {page}, Chunk: {chunk_id}]\n"
            f"{chunk['content']}"
        )

    return "\n\n".join(context_parts)


def generate_answer(question, context):
    prompt = f"""
You are a technical DevOps assistant.

Answer the user's question using ONLY the supplied context.

Instructions:
- Give a clear and technically accurate answer.
- Do not invent information that is absent from the context.
- If the context does not contain enough information, say so.
- Cite supporting information using the source page number.
- Keep the answer focused and useful.

RETRIEVED CONTEXT:

{context}

USER QUESTION:

{question}
"""

    payload = {
        "model_id": MODEL_ID,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "sampling_params": {
            "temperature": 0,
            "max_tokens": 500
        }
    }

    result = post_request(
        "/v1/inference/chat-completion",
        payload
    )

    return result["completion_message"]["content"]


def serialize_retrieval(chunks, scores):
    retrieved = []

    for index, chunk in enumerate(chunks):
        retrieved.append({
            "rank": index + 1,
            "chunk_id": chunk.get("chunk_id"),
            "content": chunk.get("content"),
            "metadata": chunk.get("metadata", {}),
            "score": (
                scores[index]
                if index < len(scores)
                else None
            )
        })

    return retrieved


def extract_sources(chunks):
    sources = {}

    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        source = metadata.get("source", "Unknown source")
        page = metadata.get("page", "Unknown page")

        sources.setdefault(source, set()).add(page)

    return [
        {
            "source": source,
            "pages": sorted(pages, key=str)
        }
        for source, pages in sources.items()
    ]


def main():
    questions = json.loads(
        QUESTIONS_PATH.read_text(encoding="utf-8")
    )

    if OUTPUT_PATH.exists():
        results = json.loads(
            OUTPUT_PATH.read_text(encoding="utf-8")
        )
    else:
        results = []

    completed_ids = {
        item["id"]
        for item in results
        if item.get("status") == "success"
    }

    pending_questions = [
        item for item in questions
        if item["id"] not in completed_ids
    ]

    print("=" * 65)
    print("LLAMASTACK BATCH RAG EVALUATION")
    print("=" * 65)
    print(f"Total questions: {len(questions)}")
    print(f"Already completed: {len(completed_ids)}")
    print(f"Remaining: {len(pending_questions)}")
    print(f"Output: {OUTPUT_PATH}")
    print("=" * 65)

    for position, item in enumerate(pending_questions, 1):
        question_id = item["id"]
        question = item["question"]

        print(
            f"\n[{position}/{len(pending_questions)}] "
            f"{question_id}: {question}",
            flush=True
        )

        start_time = time.perf_counter()

        try:
            print("Retrieving chunks...", flush=True)

            chunks, scores = retrieve_chunks(question)

            print(
                f"Retrieved {len(chunks)} chunks.",
                flush=True
            )

            context = build_context(chunks)

            print("Generating answer...", flush=True)

            answer = generate_answer(question, context)

            elapsed = round(
                time.perf_counter() - start_time,
                2
            )

            record = {
                **item,
                "framework": "LlamaStack",
                "model": MODEL_ID,
                "embedding_model": (
                    "sentence-transformers/all-MiniLM-L6-v2"
                ),
                "top_k": TOP_K,
                "status": "success",
                "generated_answer": answer,
                "retrieved_chunks": serialize_retrieval(
                    chunks, scores
                ),
                "sources": extract_sources(chunks),
                "retrieval_count": len(chunks),
                "execution_time_seconds": elapsed
            }

            print(f"Completed in {elapsed} seconds.", flush=True)

        except Exception as error:
            elapsed = round(
                time.perf_counter() - start_time,
                2
            )

            record = {
                **item,
                "framework": "LlamaStack",
                "status": "failed",
                "error": str(error),
                "execution_time_seconds": elapsed
            }

            print(
                f"FAILED: {error}",
                flush=True
            )

        results = [
            result for result in results
            if result["id"] != question_id
        ]

        results.append(record)

        # Save after every question to preserve progress.
        save_results(results)

        print(
            f"Progress saved: {len(completed_ids) + position} "
            f"of {len(questions)} questions.",
            flush=True
        )

    successful = sum(
        1 for result in results
        if result.get("status") == "success"
    )

    failed = sum(
        1 for result in results
        if result.get("status") == "failed"
    )

    print("\n" + "=" * 65)
    print("EVALUATION SUMMARY")
    print("=" * 65)
    print(f"Total questions: {len(questions)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Results saved to: {OUTPUT_PATH}")
    print("=" * 65)


if __name__ == "__main__":
    main()

import json
import sys
import urllib.error
import urllib.request


BASE_URL = "http://localhost:8321"
VECTOR_DB_ID = "llamastack_devops_rag"
MODEL_ID = "ollama/qwen2.5:3b"
TOP_K = 4


def post_request(endpoint, payload):
    url = f"{BASE_URL}{endpoint}"

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=420) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        print(f"HTTP Error {error.code}: {error.read().decode('utf-8')}")
        raise


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


def main():
    if len(sys.argv) < 2:
        print(
            'Usage: python3 evaluation/run_llamastack_rag.py '
            '"Your question here"'
        )
        sys.exit(1)

    question = " ".join(sys.argv[1:])

    print("\nRetrieving relevant chunks from FAISS...")

    chunks, scores = retrieve_chunks(question)

    print(f"Retrieved {len(chunks)} chunks.")

    context = build_context(chunks)

    print("\nGenerating answer with Qwen 2.5 3B...")

    answer = generate_answer(question, context)

    print("\n" + "=" * 65)
    print("LLAMASTACK RAG RESPONSE")
    print("=" * 65)

    print(f"\nQuestion: {question}\n")
    print(answer)

    # Display deterministic source citations from retrieved metadata.
    sources = {}

    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        source = metadata.get("source", "Unknown source")
        page = metadata.get("page", "Unknown page")

        sources.setdefault(source, set()).add(page)

    print("\n" + "-" * 65)
    print("SOURCES")
    print("-" * 65)

    for source, pages in sources.items():
        page_list = ", ".join(
            str(page) for page in sorted(pages, key=str)
        )
        print(f"- {source}: pages {page_list}")

    print("\n" + "-" * 65)
    print("RETRIEVAL DETAILS")

    for index, (chunk, score) in enumerate(zip(chunks, scores), 1):
        metadata = chunk.get("metadata", {})

        print(
            f"{index}. {chunk.get('chunk_id')} | "
            f"Page: {metadata.get('page')} | "
            f"Score: {score:.4f}"
        )

    print("\nLlamaStack RAG execution completed.")


if __name__ == "__main__":
    main()

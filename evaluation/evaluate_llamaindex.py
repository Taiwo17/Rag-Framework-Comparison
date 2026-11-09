
import json
import time
from pathlib import Path

from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.faiss import FaissVectorStore


BASE_DIR = Path(__file__).resolve().parent.parent

QUESTIONS_PATH = BASE_DIR / "evaluation" / "questions.json"
INDEX_DIR = BASE_DIR / "evaluation" / "vector_stores" / "llamaindex"
RESULTS_DIR = BASE_DIR / "evaluation" / "results"
OUTPUT_PATH = RESULTS_DIR / "llamaindex-results.json"

OLLAMA_URL = "http://172.27.224.1:11434"
MODEL_NAME = "qwen2.5:3b"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

TOP_K = 4
REQUEST_TIMEOUT = 420


def load_questions():
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def load_existing_results():
    if not OUTPUT_PATH.exists():
        return []

    return json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))


def save_results(results):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    OUTPUT_PATH.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def build_prompt(question, context):
    return f"""
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


def main():
    questions = load_questions()
    results = load_existing_results()

    completed_ids = {
        result["question_id"]
        for result in results
        if result.get("status") == "success"
    }

    print(f"Total questions: {len(questions)}")
    print(f"Already completed: {len(completed_ids)}")
    print(f"Remaining: {len(questions) - len(completed_ids)}")

    embed_model = HuggingFaceEmbedding(
        model_name=EMBEDDING_MODEL,
        device="cpu",
        normalize=True,
    )

    llm = Ollama(
        model=MODEL_NAME,
        base_url=OLLAMA_URL,
        temperature=0,
        request_timeout=REQUEST_TIMEOUT,
        additional_kwargs={"num_predict": 500},
    )

    vector_store = FaissVectorStore.from_persist_dir(
        str(INDEX_DIR)
    )

    storage_context = StorageContext.from_defaults(
        vector_store=vector_store,
        persist_dir=str(INDEX_DIR),
    )

    index = load_index_from_storage(
        storage_context=storage_context,
        embed_model=embed_model,
    )

    retriever = index.as_retriever(
        similarity_top_k=TOP_K
    )

    for position, item in enumerate(questions, start=1):
        question_id = item["id"]

        if question_id in completed_ids:
            print(f"\n[{position}/{len(questions)}] Skipping {question_id}")
            continue

        question = item["question"]
        start_time = time.time()

        print(f"\n[{position}/{len(questions)}] Evaluating {question_id}")
        print(question)

        try:
            retrieved_nodes = retriever.retrieve(question)

            context_parts = []

            for result in retrieved_nodes:
                node = result.node
                page = node.metadata.get("page", "Unknown")

                context_parts.append(
                    f"[Source: devops-rag-corpus.pdf, page {page}]\n"
                    f"{node.text}"
                )

            context = "\n\n".join(context_parts)
            prompt = build_prompt(question, context)

            response = llm.complete(prompt)
            answer = str(response).strip()

            sources = sorted({
                node.node.metadata.get("page")
                for node in retrieved_nodes
                if node.node.metadata.get("page") is not None
            })

            retrieved_chunks = []

            for result in retrieved_nodes:
                node = result.node

                retrieved_chunks.append({
                    "id": node.id_,
                    "text": node.text,
                    "metadata": node.metadata,
                    "score": result.score,
                })

            execution_time = time.time() - start_time

            result_record = {
                "question_id": question_id,
                "topic": item.get("topic"),
                "question": question,
                "expected_answer": item.get("expected_answer"),
                "source_section": item.get("source_section"),
                "framework": "LlamaIndex",
                "model": MODEL_NAME,
                "embedding_model": EMBEDDING_MODEL,
                "top_k": TOP_K,
                "status": "success",
                "generated_answer": answer,
                "retrieved_chunks": retrieved_chunks,
                "sources": sources,
                "retrieval_count": len(retrieved_nodes),
                "execution_time_seconds": round(execution_time, 2),
            }

            results = [
                record for record in results
                if record["question_id"] != question_id
            ]
            results.append(result_record)
            save_results(results)

            completed_ids.add(question_id)

            print(f"Answer: {answer}")
            print(f"Retrieved chunks: {len(retrieved_nodes)}")
            print(f"Sources: {sources}")
            print(f"Execution time: {execution_time:.2f} seconds")
            print("Result saved.")

        except Exception as error:
            execution_time = time.time() - start_time

            error_record = {
                "question_id": question_id,
                "topic": item.get("topic"),
                "question": question,
                "framework": "LlamaIndex",
                "model": MODEL_NAME,
                "embedding_model": EMBEDDING_MODEL,
                "top_k": TOP_K,
                "status": "failed",
                "error": str(error),
                "execution_time_seconds": round(execution_time, 2),
            }

            results = [
                record for record in results
                if record["question_id"] != question_id
            ]
            results.append(error_record)
            save_results(results)

            print(f"FAILED: {error}")
            print("Failure recorded. Continuing to the next question.")

    successful = sum(
        result.get("status") == "success"
        for result in results
    )

    failed = sum(
        result.get("status") == "failed"
        for result in results
    )

    print("\nEvaluation completed.")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Results: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

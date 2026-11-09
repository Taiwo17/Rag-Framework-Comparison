
import json
import time
from pathlib import Path

from haystack import Document
from haystack.dataclasses import ChatMessage
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.utils.device import ComponentDevice
from haystack_integrations.components.embedders.sentence_transformers import (
    SentenceTransformersTextEmbedder,
)
from haystack_integrations.components.generators.ollama import OllamaChatGenerator


BASE_DIR = Path(__file__).resolve().parent.parent
EMBEDDINGS_PATH = BASE_DIR / "evaluation" / "shared_embeddings.json"
QUESTIONS_PATH = BASE_DIR / "evaluation" / "questions.json"
RESULTS_DIR = BASE_DIR / "evaluation" / "results"
RESULTS_PATH = RESULTS_DIR / "haystack-results.json"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_URL = "http://172.27.224.1:11434"
LLM_MODEL = "qwen2.5:3b"
TOP_K = 4


def build_pipeline_components():
    records = json.loads(EMBEDDINGS_PATH.read_text(encoding="utf-8"))

    documents = [
        Document(
            id=record["id"],
            content=record["text"],
            embedding=record["embedding"],
            meta=record["metadata"],
        )
        for record in records
    ]

    store = InMemoryDocumentStore(
        embedding_similarity_function="cosine"
    )
    store.write_documents(documents)

    embedder = SentenceTransformersTextEmbedder(
        model=MODEL_NAME,
        normalize_embeddings=True,
        device=ComponentDevice.from_single(__import__("torch").device("cpu")),
        progress_bar=False,
    )
    embedder.warm_up()

    retriever = InMemoryEmbeddingRetriever(
        document_store=store,
        top_k=TOP_K,
        return_embedding=False,
    )

    generator = OllamaChatGenerator(
        model=LLM_MODEL,
        url=OLLAMA_URL,
        generation_kwargs={
            "temperature": 0,
            "num_predict": 500,
        },
        timeout=420,
    )

    return embedder, retriever, generator


def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

    if RESULTS_PATH.exists():
        results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    else:
        results = []

    completed_ids = {
        item["question_id"]
        for item in results
        if item.get("status") == "success"
    }

    embedder, retriever, generator = build_pipeline_components()

    for index, item in enumerate(questions, start=1):
        question_id = item["id"]

        if question_id in completed_ids:
            print(f"Skipping {question_id}: already completed.")
            continue

        question = item["question"]
        start_time = time.perf_counter()

        try:
            query_result = embedder.run(text=question)

            retrieval_result = retriever.run(
                query_embedding=query_result["embedding"]
            )

            documents = retrieval_result["documents"]

            context = "\n\n".join(
                f"[Source: devops-rag-corpus.pdf, page {doc.meta.get('page')}]\n"
                f"{doc.content}"
                for doc in documents
            )

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

            response = generator.run(
                messages=[ChatMessage.from_user(prompt)]
            )

            answer = response["replies"][0].text

            elapsed = time.perf_counter() - start_time

            record = {
                "question_id": question_id,
                "topic": item["topic"],
                "question": question,
                "expected_answer": item["expected_answer"],
                "answer": answer,
                "status": "success",
                "retrieval_count": len(documents),
                "retrieved_chunks": [
                    {
                        "id": doc.id,
                        "page": doc.meta.get("page"),
                        "score": doc.score,
                        "text": doc.content,
                    }
                    for doc in documents
                ],
                "sources": [
                    {
                        "source": "devops-rag-corpus.pdf",
                        "page": doc.meta.get("page"),
                        "chunk_id": doc.id,
                    }
                    for doc in documents
                ],
                "execution_time_seconds": round(elapsed, 2),
            }

            print(f"\n[{index}/{len(questions)}] {question_id}: SUCCESS")
            print(f"Execution time: {elapsed:.2f}s")

        except Exception as error:
            record = {
                "question_id": question_id,
                "topic": item["topic"],
                "question": question,
                "status": "failed",
                "error": str(error),
                "execution_time_seconds": round(
                    time.perf_counter() - start_time, 2
                ),
            }

            print(f"\n[{index}/{len(questions)}] {question_id}: FAILED")
            print(error)

        results.append(record)

        RESULTS_PATH.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    successful = sum(
        1 for result in results if result["status"] == "success"
    )
    failed = len(results) - successful

    print("\nEvaluation completed.")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Results: {RESULTS_PATH}")


if __name__ == "__main__":
    main()

import json
import time
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama


BASE_DIR = Path(__file__).resolve().parent.parent

QUESTIONS_PATH = BASE_DIR / "evaluation" / "questions.json"
INDEX_DIR = BASE_DIR / "evaluation" / "vector_stores" / "langchain"
RESULTS_DIR = BASE_DIR / "evaluation" / "results"
RESULTS_PATH = RESULTS_DIR / "langchain-results.json"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://172.27.224.1:11434"

TOP_K = 4


def load_questions():
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def load_existing_results():
    if not RESULTS_PATH.exists():
        return []

    return json.loads(RESULTS_PATH.read_text(encoding="utf-8"))


def save_results(results):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    RESULTS_PATH.write_text(
        json.dumps(results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def build_context(retrieved_documents):
    context_parts = []
    retrieved_chunks = []
    pages = set()

    for rank, (document, score) in enumerate(
        retrieved_documents, start=1
    ):
        metadata = document.metadata
        page = metadata.get("page")

        context_parts.append(
            f"[Source: {metadata.get('source', 'devops-rag-corpus.pdf')}, "
            f"page {page}]\n{document.page_content}"
        )

        retrieved_chunks.append({
            "rank": rank,
            "id": document.id,
            "text": document.page_content,
            "metadata": metadata,
            "score": float(score),
        })

        if page is not None:
            pages.add(page)

    return (
        "\n\n".join(context_parts),
        retrieved_chunks,
        sorted(pages),
    )


def build_prompt(context, question):
    return f"""You are a technical DevOps assistant.

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

    pending_questions = [
        question
        for question in questions
        if question["id"] not in completed_ids
    ]

    print(f"Total questions: {len(questions)}")
    print(f"Already completed: {len(completed_ids)}")
    print(f"Remaining: {len(pending_questions)}")

    if not pending_questions:
        print("All questions have already been evaluated.")
        return

    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    vector_store = FAISS.load_local(
        str(INDEX_DIR),
        embeddings,
        allow_dangerous_deserialization=True,
    )

    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_URL,
        temperature=0,
        num_predict=500,
        client_kwargs={"timeout": 420},
    )

    for index, item in enumerate(pending_questions, start=1):
        question_id = item["id"]
        question = item["question"]

        print("\n" + "=" * 60)
        print(f"Question {index}/{len(pending_questions)}: {question_id}")
        print(question)

        start_time = time.perf_counter()

        try:
            retrieved_documents = (
                vector_store.similarity_search_with_score(
                    question,
                    k=TOP_K,
                )
            )

            context, retrieved_chunks, pages = build_context(
                retrieved_documents
            )

            prompt = build_prompt(context, question)

            response = llm.invoke(prompt)
            answer = response.content

            execution_time = time.perf_counter() - start_time

            record = {
                **item,
                "framework": "LangChain",
                "model": OLLAMA_MODEL,
                "embedding_model": MODEL_NAME,
                "top_k": TOP_K,
                "status": "success",
                "generated_answer": answer,
                "retrieved_chunks": retrieved_chunks,
                "sources": pages,
                "retrieval_count": len(retrieved_chunks),
                "execution_time_seconds": round(execution_time, 2),
            }

            print(f"\nAnswer: {answer}")
            print(f"Retrieved chunks: {len(retrieved_chunks)}")
            print(f"Execution time: {execution_time:.2f} seconds")

        except Exception as error:
            execution_time = time.perf_counter() - start_time

            record = {
                **item,
                "framework": "LangChain",
                "model": OLLAMA_MODEL,
                "embedding_model": MODEL_NAME,
                "top_k": TOP_K,
                "status": "failed",
                "generated_answer": None,
                "retrieved_chunks": [],
                "sources": [],
                "retrieval_count": 0,
                "execution_time_seconds": round(execution_time, 2),
                "error": str(error),
            }

            print(f"\nFailed: {error}")

        results.append(record)
        save_results(results)

        print(f"Saved progress for {question_id}.")

    successful = sum(
        1 for result in results
        if result.get("status") == "success"
    )

    failed = sum(
        1 for result in results
        if result.get("status") == "failed"
    )

    print("\n" + "=" * 60)
    print("LANGCHAIN EVALUATION COMPLETED")
    print("=" * 60)
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Results: {RESULTS_PATH}")


if __name__ == "__main__":
    main()
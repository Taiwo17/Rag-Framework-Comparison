import json
import time
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage


BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_DIR = BASE_DIR / "evaluation" / "vector_stores" / "langchain"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://172.27.224.1:11434"

TOP_K = 4


SYSTEM_PROMPT = """You are a technical assistant answering questions about DevOps.

Answer the user's question using only the supplied context.

Instructions:
- Give a clear, accurate, and direct answer.
- Do not introduce facts that are not supported by the context.
- If the context does not contain enough information, state that clearly.
- Do not invent details or assumptions.
- Keep the answer concise and relevant.
"""


def main():
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
        num_ctx=4096,
    )

    question = input("Enter your question: ").strip()

    if not question:
        raise ValueError("Question cannot be empty.")

    start_time = time.perf_counter()

    retrieved_results = vector_store.similarity_search_with_score(
        question,
        k=TOP_K,
    )

    context_parts = []
    sources = []

    for document, score in retrieved_results:
        page = document.metadata.get("page")
        source = document.metadata.get("source", "devops-rag-corpus.pdf")

        context_parts.append(
            f"[Source: {source}, page {page}]\n{document.page_content}"
        )

        sources.append({
            "chunk_id": document.id,
            "source": source,
            "page": page,
            "score": float(score),
        })

    context = "\n\n".join(context_parts)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=f"""Context:

{context}

Question:
{question}

Answer:"""
        ),
    ]

    response = llm.invoke(messages)
    answer = response.content

    execution_time = time.perf_counter() - start_time

    print("\n" + "=" * 60)
    print("LANGCHAIN RAG RESPONSE")
    print("=" * 60)

    print(f"\nQuestion: {question}")
    print(f"\nAnswer:\n{answer}")

    print("\nRetrieved sources:")
    for source in sources:
        print(
            f"- {source['chunk_id']} | "
            f"Page {source['page']} | "
            f"Score: {source['score']:.6f}"
        )

    print(f"\nRetrieved chunks: {len(retrieved_results)}")
    print(f"Execution time: {execution_time:.2f} seconds")


if __name__ == "__main__":
    main()
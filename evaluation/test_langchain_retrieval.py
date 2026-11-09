from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings


BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_DIR = BASE_DIR / "evaluation" / "vector_stores" / "langchain"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 4


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

    question = "How does Docker make application deployment portable?"

    results = vector_store.similarity_search_with_score(
        question,
        k=TOP_K,
    )

    print(f"\nQuestion: {question}")
    print(f"Retrieved chunks: {len(results)}")

    for rank, (document, score) in enumerate(results, start=1):
        print(f"\nRank: {rank}")
        print(f"Chunk ID: {document.id}")
        print(f"Page: {document.metadata.get('page')}")
        print(f"Score: {score:.6f}")
        print(f"Text: {document.page_content[:300]}")


if __name__ == "__main__":
    main()
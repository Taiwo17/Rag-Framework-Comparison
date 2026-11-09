import json
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import DistanceStrategy
from langchain_huggingface import HuggingFaceEmbeddings


BASE_DIR = Path(__file__).resolve().parent.parent

EMBEDDINGS_PATH = BASE_DIR / "evaluation" / "shared_embeddings.json"
OUTPUT_DIR = BASE_DIR / "evaluation" / "vector_stores" / "langchain"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EXPECTED_DIMENSIONS = 384


def main():
    records = json.loads(EMBEDDINGS_PATH.read_text(encoding="utf-8"))

    if not records:
        raise ValueError("No embeddings found.")

    ids = [record["id"] for record in records]

    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate chunk IDs detected.")

    vectors = [record["embedding"] for record in records]

    if any(len(vector) != EXPECTED_DIMENSIONS for vector in vectors):
        raise ValueError("Unexpected embedding dimensions.")

    print(f"Loaded {len(records)} shared embeddings.")
    print(f"Embedding dimensions: {EXPECTED_DIMENSIONS}")

    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    text_embeddings = [
        (record["text"], record["embedding"])
        for record in records
    ]

    metadatas = [
        record["metadata"]
        for record in records
    ]

    vector_store = FAISS.from_embeddings(
        text_embeddings=text_embeddings,
        embedding=embeddings,
        metadatas=metadatas,
        ids=ids,
        distance_strategy=DistanceStrategy.MAX_INNER_PRODUCT,
        normalize_L2=False,
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(OUTPUT_DIR))

    print("\nLangChain FAISS index created successfully.")
    print(f"Documents indexed: {len(records)}")
    print(f"Similarity: inner product")
    print(f"Output: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
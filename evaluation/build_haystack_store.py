
import json
from pathlib import Path

from haystack import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore


BASE_DIR = Path(__file__).resolve().parent.parent
EMBEDDINGS_PATH = BASE_DIR / "evaluation" / "shared_embeddings.json"
OUTPUT_PATH = BASE_DIR / "evaluation" / "haystack_store.json"


def main():
    records = json.loads(EMBEDDINGS_PATH.read_text(encoding="utf-8"))

    if not records:
        raise ValueError("No shared embeddings found.")

    documents = []

    for record in records:
        embedding = record["embedding"]

        if len(embedding) != 384:
            raise ValueError(f"Invalid embedding dimensions: {record['id']}")

        documents.append(
            Document(
                id=record["id"],
                content=record["text"],
                embedding=embedding,
                meta=record["metadata"],
            )
        )

    store = InMemoryDocumentStore(
        embedding_similarity_function="cosine"
    )

    store.write_documents(documents)

    OUTPUT_PATH.write_text(
        json.dumps(
            {
                "document_count": store.count_documents(),
                "embedding_dimensions": 384,
                "similarity": "cosine",
                "document_ids": [doc.id for doc in documents],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Haystack document store created.")
    print(f"Documents indexed: {store.count_documents()}")
    print("Embedding dimensions: 384")
    print("Similarity: cosine")


if __name__ == "__main__":
    main()


import json
import torch
from pathlib import Path

from haystack import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack_integrations.components.embedders.sentence_transformers import (
    SentenceTransformersTextEmbedder,
)
from haystack.utils.device import ComponentDevice


BASE_DIR = Path(__file__).resolve().parent.parent
EMBEDDINGS_PATH = BASE_DIR / "evaluation" / "shared_embeddings.json"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
QUESTION = "How does Docker make application deployment portable?"


def main():
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
        device=ComponentDevice.from_single(torch.device("cpu")),
        progress_bar=False,
    )
    embedder.warm_up()

    query_result = embedder.run(text=QUESTION)
    query_embedding = query_result["embedding"]

    retriever = InMemoryEmbeddingRetriever(
        document_store=store,
        top_k=4,
        return_embedding=False,
    )

    result = retriever.run(query_embedding=query_embedding)
    retrieved_documents = result["documents"]

    print(f"Question: {QUESTION}")
    print(f"Retrieved chunks: {len(retrieved_documents)}")

    for document in retrieved_documents:
        print(
            f"\nID: {document.id}"
            f"\nPage: {document.meta.get('page')}"
            f"\nScore: {document.score}"
            f"\nText: {document.content[:250]}..."
        )


if __name__ == "__main__":
    main()

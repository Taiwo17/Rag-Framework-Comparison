
import json
from pathlib import Path

import faiss  # pyright: ignore[reportMissingImports]
from llama_index.core import StorageContext, VectorStoreIndex
from llama_index.core.schema import TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore


BASE_DIR = Path(__file__).resolve().parent.parent
EMBEDDINGS_PATH = BASE_DIR / "evaluation" / "shared_embeddings.json"

DIMENSIONS = 384
VECTOR_STORE_DIR = BASE_DIR / "evaluation" / "vector_stores" / "llamaindex"


def main():
    records = json.loads(EMBEDDINGS_PATH.read_text(encoding="utf-8"))

    if not records:
        raise ValueError("No shared embeddings found.")

    nodes = []

    for record in records:
        embedding = record["embedding"]

        if len(embedding) != DIMENSIONS:
            raise ValueError(
                f"Invalid embedding dimension for {record['id']}"
            )

        nodes.append(
            TextNode(
                id_=record["id"],
                text=record["text"],
                metadata=record["metadata"],
                embedding=embedding,
            )
        )

    print(f"Loaded {len(nodes)} shared chunks.")

    faiss_index = faiss.IndexFlatIP(DIMENSIONS)
    vector_store = FaissVectorStore(faiss_index=faiss_index)

    storage_context = StorageContext.from_defaults(
        vector_store=vector_store
    )

    embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        device="cpu",
        normalize=True,
    )

    index = VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        show_progress=True,
    )

    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(VECTOR_STORE_DIR))

    print("\nLlamaIndex indexing completed.")
    print(f"Indexed chunks: {len(nodes)}")
    print(f"Vector dimensions: {DIMENSIONS}")
    print(f"FAISS vectors: {faiss_index.ntotal}")
    print(f"Index location: {VECTOR_STORE_DIR}")


if __name__ == "__main__":
    main()

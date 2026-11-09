
from pathlib import Path

from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.faiss import FaissVectorStore


BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_DIR = BASE_DIR / "evaluation" / "vector_stores" / "llamaindex"

QUESTION = "How does Docker improve application portability?"


def main():
    embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        device="cpu",
        normalize=True,
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

    retriever = index.as_retriever(similarity_top_k=4)
    results = retriever.retrieve(QUESTION)

    print(f"\nQuestion: {QUESTION}")
    print(f"Retrieved chunks: {len(results)}\n")

    for position, result in enumerate(results, start=1):
        node = result.node

        print(f"Result {position}")
        print(f"Chunk ID: {node.id_}")
        print(f"Page: {node.metadata.get('page')}")
        print(f"Chunk index: {node.metadata.get('chunk_index')}")
        print(f"Similarity score: {result.score:.6f}")
        print(f"Text: {node.text[:400]}")
        print("-" * 70)


if __name__ == "__main__":
    main()

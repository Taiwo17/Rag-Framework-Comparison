import json
from pathlib import Path 

from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent.parent

CHUNKS_PATH = BASE_DIR / "evaluation" / "shared_chunks.json"
OUTPUT_PATH = BASE_DIR / "evaluation" / "shared_embeddings.json"
CONFIG_PATH = BASE_DIR / "configs" / "rag-config.json"


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))

    model_name = config["embeddings"]["model"]

    print(f"Loading embedding model: {model_name}")

    model = SentenceTransformer(model_name)

    texts = [chunk["text"] for chunk in chunks] 

    print(f"Generating embeddings for {len(texts)} chunks...")

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True
    )

    results = []

    for chunk, embedding in zip(chunks, embeddings):
        results.append({
            "id": chunk["id"],
            "text": chunk["text"],
            "metadata": chunk["metadata"],
            "embedding": embedding.tolist()
        })

    OUTPUT_PATH.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print("\nEmbedding generation completed.")
    print(f"Total embeddings: {len(results)}")
    print(f"Embedding dimensions: {embeddings.shape[1]}")
    print(f"Output: {OUTPUT_PATH}")

if __name__ == "__main__":
    main()


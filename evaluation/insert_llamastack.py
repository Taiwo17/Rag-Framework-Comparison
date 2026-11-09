import json
import urllib.request
import urllib.error
from pathlib import Path

API_URL = "http://localhost:8321/v1/vector-io/insert"
VECTOR_DB_ID = "llamastack_devops_rag"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

data = json.loads(
    Path("evaluation/shared_embeddings.json").read_text(encoding="utf-8")
)

if len(data) != 20:
    raise ValueError(f"Expected 20 records, found {len(data)}")

ids = [item["id"] for item in data]

if len(ids) != len(set(ids)):
    raise ValueError("Duplicate chunk IDs detected")

chunks = []

for item in data:
    embedding = item["embedding"]

    if len(embedding) != 384:
        raise ValueError(f"Invalid embedding dimension: {item['id']}")

    chunks.append({
        "content": item["text"],
        "embedding": embedding,
        "metadata": {**item["metadata"], "document_id": "devops-rag-corpus"},
        "chunk_id": item["id"],
        "chunk_metadata": {
            "chunk_id": item["id"],
            "document_id": "devops-rag-corpus",
            "source": item["metadata"]["source"],
            "chunk_embedding_model": EMBEDDING_MODEL,
            "chunk_embedding_dimension": 384
        }
    })

payload = {
    "vector_db_id": VECTOR_DB_ID,
    "chunks": chunks
}

request = urllib.request.Request(
    API_URL,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

try:
    with urllib.request.urlopen(request, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))
        print(json.dumps(result, indent=2))
except urllib.error.HTTPError as error:
    print(f"HTTP Error: {error.code}")
    print(error.read().decode("utf-8"))
    raise

print(f"\nSuccessfully submitted {len(chunks)} chunks to LlamaStack.")

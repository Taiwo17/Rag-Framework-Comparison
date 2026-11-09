
import json
from pathlib import Path

from haystack import Document
from haystack.dataclasses import ChatMessage
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.utils.device import ComponentDevice
from haystack_integrations.components.embedders.sentence_transformers import (
    SentenceTransformersTextEmbedder,
)
from haystack_integrations.components.generators.ollama import OllamaChatGenerator


BASE_DIR = Path(__file__).resolve().parent.parent
EMBEDDINGS_PATH = BASE_DIR / "evaluation" / "shared_embeddings.json"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_URL = "http://172.27.224.1:11434"
LLM_MODEL = "qwen2.5:3b"
TOP_K = 4


def build_document_store():
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

    return store


def main():
    store = build_document_store()

    embedder = SentenceTransformersTextEmbedder(
        model=MODEL_NAME,
        normalize_embeddings=True,
        device=ComponentDevice.from_single(__import__("torch").device("cpu")),
        progress_bar=False,
    )
    embedder.warm_up()

    retriever = InMemoryEmbeddingRetriever(
        document_store=store,
        top_k=TOP_K,
        return_embedding=False,
    )

    generator = OllamaChatGenerator(
        model=LLM_MODEL,
        url=OLLAMA_URL,
        generation_kwargs={
            "temperature": 0,
            "num_predict": 500,
        },
        timeout=420,
    )

    question = "How does Docker make application deployment portable?"

    query_result = embedder.run(text=question)
    retrieval_result = retriever.run(
        query_embedding=query_result["embedding"]
    )

    documents = retrieval_result["documents"]

    context = "\n\n".join(
        f"[Source: devops-rag-corpus.pdf, page {doc.meta.get('page')}]\n"
        f"{doc.content}"
        for doc in documents
    )

    prompt = f"""
You are a technical DevOps assistant.

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

    response = generator.run(
        messages=[ChatMessage.from_user(prompt)]
    )

    print(f"Question: {question}")
    print("\nAnswer:")
    print(response["replies"][0].text)

    print("\nRetrieved sources:")
    for doc in documents:
        print(
            f"- {doc.id} | "
            f"Page {doc.meta.get('page')} | "
            f"Score: {doc.score:.4f}"
        )


if __name__ == "__main__":
    main()

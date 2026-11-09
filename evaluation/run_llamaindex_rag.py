
import time
from pathlib import Path

from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.faiss import FaissVectorStore


BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_DIR = BASE_DIR / "evaluation" / "vector_stores" / "llamaindex"

OLLAMA_URL = "http://172.27.224.1:11434"
MODEL_NAME = "qwen2.5:3b"
TOP_K = 4

QUESTION = "How does Docker improve application portability?"


def main():
    start_time = time.time()

    embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        device="cpu",
        normalize=True,
    )

    llm = Ollama(
        model=MODEL_NAME,
        base_url=OLLAMA_URL,
        temperature=0,
        request_timeout=420,
        additional_kwargs={"num_predict": 500},
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

    retriever = index.as_retriever(
        similarity_top_k=TOP_K
    )

    retrieved_nodes = retriever.retrieve(QUESTION)

    context_parts = []

    for result in retrieved_nodes:
        node = result.node
        page = node.metadata.get("page", "Unknown")

        context_parts.append(
            f"[Source: devops-rag-corpus.pdf, page {page}]\n"
            f"{node.text}"
        )

    context = "\n\n".join(context_parts)

    # Shared evaluation prompt used by both LlamaStack and LlamaIndex.
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

{QUESTION}
"""

    response = llm.complete(prompt)

    print("\nQUESTION")
    print(QUESTION)

    print("\nANSWER")
    print(str(response))

    print("\nRETRIEVED SOURCES")

    for result in retrieved_nodes:
        node = result.node
        print(
            f"- {node.id_}: "
            f"page {node.metadata.get('page')}, "
            f"score {result.score:.6f}"
        )

    print(
        f"\nExecution time: {time.time() - start_time:.2f} seconds"
    )


if __name__ == "__main__":
    main()

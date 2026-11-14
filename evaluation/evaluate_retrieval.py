
import argparse
import json
import math
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

EVALUATION_DIR = BASE_DIR / "evaluation"
QUESTIONS_PATH = EVALUATION_DIR / "questions.json"
JUDGMENTS_PATH = EVALUATION_DIR / "relevance_judgments.json"
EMBEDDINGS_PATH = EVALUATION_DIR / "shared_embeddings.json"

RESULTS_DIR = EVALUATION_DIR / "results" / "retrieval"

TOP_K = 4
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DEVICE = "cpu"
NORMALIZE_EMBEDDINGS = True

OLLAMA_URL = "http://172.27.224.1:11434"

LLAMASTACK_URL = "http://localhost:8321"
LLAMASTACK_VECTOR_DB_ID = "llamastack_devops_rag"
LLAMASTACK_EMBEDDING_MODEL = "ollama/all-minilm:l6-v2"
LLAMASTACK_TIMEOUT = 120

FRAMEWORKS = {
    "langchain": {
        "name": "LangChain",
        "index_dir": EVALUATION_DIR / "vector_stores" / "langchain",
    },
    "llamaindex": {
        "name": "LlamaIndex",
        "index_dir": EVALUATION_DIR / "vector_stores" / "llamaindex",
    },
    "haystack": {
        "name": "Haystack",
    },
    "llamastack": {
        "name": "LlamaStack",
    },
}


def load_json(path):
    if not path.is_file():
        raise FileNotFoundError(f"Required file not found: {path}")

    return json.loads(path.read_text(encoding="utf-8"))


def load_inputs():
    questions = load_json(QUESTIONS_PATH)
    relevance_data = load_json(JUDGMENTS_PATH)

    judgments = relevance_data.get("judgments", {})
    configured_top_k = relevance_data.get("metrics", {}).get("top_k")

    if configured_top_k != TOP_K:
        raise ValueError(
            f"TOP_K mismatch: evaluator uses {TOP_K}, "
            f"but relevance judgments specify {configured_top_k}."
        )

    question_ids = {item["id"] for item in questions}

    missing_judgments = question_ids - set(judgments)

    if missing_judgments:
        raise ValueError(
            f"Missing relevance judgments for: "
            f"{sorted(missing_judgments)}"
        )

    for question_id, chunk_grades in judgments.items():
        for chunk_id, grade in chunk_grades.items():
            if grade not in (0, 1, 2):
                raise ValueError(
                    f"Invalid relevance grade for "
                    f"{question_id}/{chunk_id}: {grade}"
                )

    return questions, judgments


def get_stable_chunk_id(document, metadata):
    document_id = getattr(document, "id", None)

    if document_id:
        return str(document_id)

    document_id = metadata.get("document_id")
    chunk_index = metadata.get("chunk_index")

    if document_id is not None and chunk_index is not None:
        return f"{document_id}:{chunk_index}"

    raise ValueError(
        "Retrieved document does not have a stable chunk ID."
    )


def normalize_chunk(rank, chunk_id, text, metadata=None, score=None):
    if not chunk_id:
        raise ValueError(
            f"Retrieved chunk at rank {rank} has no stable ID."
        )

    if not text:
        raise ValueError(
            f"Retrieved chunk {chunk_id} has no text."
        )

    normalized_score = None

    if score is not None:
        normalized_score = float(score)

    return {
        "rank": rank,
        "chunk_id": str(chunk_id),
        "text": str(text),
        "metadata": metadata or {},
        "score": normalized_score,
    }


def retrieve_langchain(questions):
    from langchain_community.vectorstores import FAISS
    from langchain_huggingface import HuggingFaceEmbeddings

    index_dir = FRAMEWORKS["langchain"]["index_dir"]

    if not index_dir.is_dir():
        raise FileNotFoundError(
            f"LangChain FAISS index not found: {index_dir}"
        )

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": EMBEDDING_DEVICE},
        encode_kwargs={
            "normalize_embeddings": NORMALIZE_EMBEDDINGS
        },
    )

    vector_store = FAISS.load_local(
        str(index_dir),
        embeddings,
        allow_dangerous_deserialization=True,
    )

    results = []

    for item in questions:
        start_time = time.perf_counter()

        documents = vector_store.similarity_search_with_score(
            item["question"],
            k=TOP_K,
        )

        chunks = []

        for rank, (document, score) in enumerate(
            documents, start=1
        ):
            metadata = dict(document.metadata or {})

            chunks.append(
                normalize_chunk(
                    rank=rank,
                    chunk_id=get_stable_chunk_id(
                        document, metadata
                    ),
                    text=document.page_content,
                    metadata=metadata,
                    score=score,
                )
            )

        results.append(
            build_question_result(
                item,
                chunks,
                time.perf_counter() - start_time,
            )
        )

    return results


def retrieve_llamaindex(questions):
    from llama_index.core import (
        StorageContext,
        load_index_from_storage,
    )
    from llama_index.embeddings.huggingface import (
        HuggingFaceEmbedding,
    )
    from llama_index.vector_stores.faiss import (
        FaissVectorStore,
    )

    index_dir = FRAMEWORKS["llamaindex"]["index_dir"]

    if not index_dir.is_dir():
        raise FileNotFoundError(
            f"LlamaIndex index not found: {index_dir}"
        )

    embed_model = HuggingFaceEmbedding(
        model_name=EMBEDDING_MODEL,
        device=EMBEDDING_DEVICE,
        normalize=NORMALIZE_EMBEDDINGS,
    )

    vector_store = FaissVectorStore.from_persist_dir(
        str(index_dir)
    )

    storage_context = StorageContext.from_defaults(
        vector_store=vector_store,
        persist_dir=str(index_dir),
    )

    index = load_index_from_storage(
        storage_context=storage_context,
        embed_model=embed_model,
    )

    retriever = index.as_retriever(
        similarity_top_k=TOP_K
    )

    results = []

    for item in questions:
        start_time = time.perf_counter()

        retrieved_nodes = retriever.retrieve(
            item["question"]
        )

        chunks = []

        for rank, result in enumerate(
            retrieved_nodes, start=1
        ):
            node = result.node
            metadata = dict(node.metadata or {})

            chunk_id = getattr(node, "id_", None)

            if not chunk_id:
                document_id = metadata.get("document_id")
                chunk_index = metadata.get("chunk_index")

                if (
                    document_id is not None
                    and chunk_index is not None
                ):
                    chunk_id = f"{document_id}:{chunk_index}"

            chunks.append(
                normalize_chunk(
                    rank=rank,
                    chunk_id=chunk_id,
                    text=node.text,
                    metadata=metadata,
                    score=result.score,
                )
            )

        results.append(
            build_question_result(
                item,
                chunks,
                time.perf_counter() - start_time,
            )
        )

    return results


def retrieve_haystack(questions):
    import torch

    from haystack import Document
    from haystack.document_stores.in_memory import (
        InMemoryDocumentStore,
    )
    from haystack.components.retrievers.in_memory import (
        InMemoryEmbeddingRetriever,
    )
    from haystack.utils.device import ComponentDevice
    from haystack_integrations.components.embedders.sentence_transformers import (
        SentenceTransformersTextEmbedder,
    )

    embedding_records = load_json(EMBEDDINGS_PATH)

    documents = [
        Document(
            id=record["id"],
            content=record["text"],
            embedding=record["embedding"],
            meta=record["metadata"],
        )
        for record in embedding_records
    ]

    store = InMemoryDocumentStore(
        embedding_similarity_function="cosine"
    )

    store.write_documents(documents)

    embedder = SentenceTransformersTextEmbedder(
        model=EMBEDDING_MODEL,
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        device=ComponentDevice.from_single(
            torch.device(EMBEDDING_DEVICE)
        ),
        progress_bar=False,
    )

    embedder.warm_up()

    retriever = InMemoryEmbeddingRetriever(
        document_store=store,
        top_k=TOP_K,
        return_embedding=False,
    )

    results = []

    for item in questions:
        start_time = time.perf_counter()

        query_result = embedder.run(
            text=item["question"]
        )

        retrieval_result = retriever.run(
            query_embedding=query_result["embedding"]
        )

        chunks = []

        for rank, document in enumerate(
            retrieval_result["documents"], start=1
        ):
            metadata = dict(document.meta or {})

            chunk_id = get_stable_chunk_id(
                document, metadata
            )

            chunks.append(
                normalize_chunk(
                    rank=rank,
                    chunk_id=chunk_id,
                    text=document.content,
                    metadata=metadata,
                    score=document.score,
                )
            )

        results.append(
            build_question_result(
                item,
                chunks,
                time.perf_counter() - start_time,
            )
        )

    return results


def llamastack_post(endpoint, payload):
    url = f"{LLAMASTACK_URL}{endpoint}"

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=LLAMASTACK_TIMEOUT,
        ) as response:
            return json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")

        raise RuntimeError(
            f"LlamaStack HTTP {error.code}: {body}"
        ) from error


def retrieve_llamastack(questions):
    results = []

    for item in questions:
        start_time = time.perf_counter()

        response = llamastack_post(
            "/v1/vector-io/query",
            {
                "vector_db_id": LLAMASTACK_VECTOR_DB_ID,
                "query": item["question"],
                "params": {
                    "max_chunks": TOP_K
                },
            },
        )

        returned_chunks = response.get("chunks", [])
        returned_scores = response.get("scores", [])

        chunks = []

        for rank, chunk in enumerate(
            returned_chunks, start=1
        ):
            metadata = chunk.get("metadata") or {}

            chunk_id = (
                chunk.get("chunk_id")
                or chunk.get("id")
            )

            if not chunk_id:
                document_id = metadata.get("document_id")
                chunk_index = metadata.get("chunk_index")

                if (
                    document_id is not None
                    and chunk_index is not None
                ):
                    chunk_id = f"{document_id}:{chunk_index}"

            text = (
                chunk.get("content")
                or chunk.get("text")
            )

            score = (
                returned_scores[rank - 1]
                if rank - 1 < len(returned_scores)
                else chunk.get("score")
            )

            chunks.append(
                normalize_chunk(
                    rank=rank,
                    chunk_id=chunk_id,
                    text=text,
                    metadata=metadata,
                    score=score,
                )
            )

        results.append(
            build_question_result(
                item,
                chunks,
                time.perf_counter() - start_time,
            )
        )

    return results


def build_question_result(item, chunks, elapsed):
    if len(chunks) > TOP_K:
        raise ValueError(
            f"{item['id']} returned {len(chunks)} chunks; "
            f"maximum allowed is {TOP_K}."
        )

    chunk_ids = [chunk["chunk_id"] for chunk in chunks]

    if len(chunk_ids) != len(set(chunk_ids)):
        raise ValueError(
            f"{item['id']} returned duplicate chunk IDs."
        )

    return {
        "question_id": item["id"],
        "question": item["question"],
        "requested_top_k": TOP_K,
        "retrieved_count": len(chunks),
        "retrieved_chunks": chunks,
        "retrieval_time_seconds": round(elapsed, 6),
    }


def calculate_dcg(grades):
    return sum(
        (2 ** grade - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(grades, start=1)
    )


def calculate_metrics(retrieved_chunks, question_judgments):
    retrieved_grades = [
        question_judgments.get(chunk["chunk_id"], 0)
        for chunk in retrieved_chunks
    ]

    relevant_count = sum(
        grade >= 1 for grade in retrieved_grades
    )

    precision = relevant_count / TOP_K

    reciprocal_rank = 0.0

    for rank, grade in enumerate(
        retrieved_grades, start=1
    ):
        if grade >= 1:
            reciprocal_rank = 1 / rank
            break

    ideal_grades = sorted(
        question_judgments.values(),
        reverse=True,
    )[:TOP_K]

    ideal_dcg = calculate_dcg(ideal_grades)
    actual_dcg = calculate_dcg(retrieved_grades)

    ndcg = (
        actual_dcg / ideal_dcg
        if ideal_dcg > 0
        else 0.0
    )

    return {
        "precision_at_4": round(precision, 6),
        "mrr_at_4": round(reciprocal_rank, 6),
        "ndcg_at_4": round(ndcg, 6),
        "relevant_chunks_retrieved": relevant_count,
        "retrieved_grades": retrieved_grades,
    }


def evaluate_results(framework, results, judgments):
    evaluated_questions = []

    for result in results:
        question_id = result["question_id"]

        metrics = calculate_metrics(
            result["retrieved_chunks"],
            judgments[question_id],
        )

        evaluated_questions.append({
            **result,
            "metrics": metrics,
        })

    question_count = len(evaluated_questions)

    if question_count == 0:
        raise ValueError("No questions were evaluated.")

    averages = {
        metric: round(
            sum(
                question["metrics"][metric]
                for question in evaluated_questions
            ) / question_count,
            6,
        )
        for metric in (
            "precision_at_4",
            "mrr_at_4",
            "ndcg_at_4",
        )
    }

    return {
        "framework": framework,
        "evaluated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "embedding_model": (
            LLAMASTACK_EMBEDDING_MODEL
            if framework == "LlamaStack"
            else EMBEDDING_MODEL
        ),
        "top_k": TOP_K,
        "question_count": question_count,
        "metrics": {
            "averages": averages,
            "per_question": evaluated_questions,
        },
        "notes": {
            "precision": (
                "Relevant chunks have relevance grade >= 1. "
                "Denominator is requested top_k."
            ),
            "mrr": (
                "Reciprocal rank of the first chunk "
                "with relevance grade >= 1."
            ),
            "ndcg": (
                "Uses graded relevance values 0, 1 and 2."
            ),
            "recall": (
                "Deferred until the complete relevant chunk "
                "set is established for every question."
            ),
            "native_scores": (
                "Framework-native retrieval scores are diagnostic "
                "only and must not be compared across frameworks."
            ),
        },
    }


def save_output(framework_key, output):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    output_path = (
        RESULTS_DIR / f"{framework_key}-retrieval.json"
    )

    output_path.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Run retrieval-only evaluation for one RAG framework."
        )
    )

    parser.add_argument(
        "--framework",
        required=True,
        choices=FRAMEWORKS.keys(),
        help="Framework to evaluate.",
    )

    args = parser.parse_args()

    framework_key = args.framework
    framework_name = FRAMEWORKS[framework_key]["name"]

    print("=" * 65)
    print("RETRIEVAL-ONLY EVALUATION")
    print("=" * 65)
    print(f"Framework: {framework_name}")
    print(f"Top K: {TOP_K}")
    print("LLM generation: DISABLED")
    print("=" * 65)

    questions, judgments = load_inputs()

    print(f"Questions loaded: {len(questions)}")
    print("Loading framework retriever...")

    retrieval_functions = {
        "langchain": retrieve_langchain,
        "llamaindex": retrieve_llamaindex,
        "haystack": retrieve_haystack,
        "llamastack": retrieve_llamastack,
    }

    retrieval_function = retrieval_functions[framework_key]

    results = retrieval_function(questions)

    if len(results) != len(questions):
        raise RuntimeError(
            f"Expected {len(questions)} results, "
            f"received {len(results)}."
        )

    print(f"\nRetrieved results: {len(results)}")

    output = evaluate_results(
        framework_name,
        results,
        judgments,
    )

    output_path = save_output(
        framework_key,
        output,
    )

    print("\n" + "=" * 65)
    print("RETRIEVAL EVALUATION SUMMARY")
    print("=" * 65)

    averages = output["metrics"]["averages"]

    print(f"Framework: {framework_name}")
    print(f"Questions: {output['question_count']}")
    print(f"Precision@4: {averages['precision_at_4']:.4f}")
    print(f"MRR@4:       {averages['mrr_at_4']:.4f}")
    print(f"nDCG@4:      {averages['ndcg_at_4']:.4f}")
    print(f"\nOutput: {output_path}")
    print("=" * 65)


if __name__ == "__main__":
    main()


import json
import statistics
import time
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

try:
    from .result_schema import (
        build_result,
        load_results,
        save_results,
    )
    from .run_tracking import (
        build_run_metadata,
        calculate_file_hash,
        initialize_run,
        get_package_version,
    )
except ImportError:
    from result_schema import (
        build_result,
        load_results,
        save_results,
    )
    from run_tracking import (
        build_run_metadata,
        calculate_file_hash,
        initialize_run,
        get_package_version,
    )


BASE_DIR = Path(__file__).resolve().parent.parent

CORPUS_PATH = BASE_DIR / "corpus" / "devops-rag-corpus.pdf"
EMBEDDINGS_PATH = BASE_DIR / "evaluation" / "shared_embeddings.json"
QUESTIONS_PATH = BASE_DIR / "evaluation" / "questions.json"

RESULTS_DIR = BASE_DIR / "evaluation" / "results"
RESULTS_PATH = RESULTS_DIR / "haystack-results.json"
RUN_METADATA_PATH = RESULTS_PATH.with_suffix(".run.json")

FRAMEWORK_NAME = "Haystack"
FRAMEWORK_PACKAGE = "haystack-ai"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_URL = "http://172.27.224.1:11434"
LLM_MODEL = "qwen2.5:3b"

TOP_K = 4
TEMPERATURE = 0
MAX_TOKENS = 500
GENERATION_TIMEOUT_SECONDS = 420

NORMALIZE_EMBEDDINGS = True
EMBEDDING_DEVICE = "cpu"
SIMILARITY_FUNCTION = "cosine"

WARMUP_RUNS = 1
MEASUREMENT_RUNS = 3


PROMPT_TEMPLATE = """You are a technical DevOps assistant.

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


def create_current_run_metadata():
    """Build metadata for the current Haystack evaluation configuration."""

    return build_run_metadata(
        framework=FRAMEWORK_NAME,
        package_name=FRAMEWORK_PACKAGE,
        model=LLM_MODEL,
        embedding_model=MODEL_NAME,
        top_k=TOP_K,
        corpus_path=CORPUS_PATH,
        config={
            "questions_sha256": calculate_file_hash(QUESTIONS_PATH),
            "shared_embeddings_sha256": calculate_file_hash(
                EMBEDDINGS_PATH
            ),
            "haystack_integrations_versions": {
                "sentence_transformers": get_package_version(
                    "sentence-transformers-haystack"
                ),
                "ollama": get_package_version("ollama-haystack"),
            },
            "ollama_url": OLLAMA_URL,
            "embedding_device": EMBEDDING_DEVICE,
            "normalize_embeddings": NORMALIZE_EMBEDDINGS,
            "similarity_function": SIMILARITY_FUNCTION,
            "retriever": "InMemoryEmbeddingRetriever",
            "retrieval_top_k": TOP_K,
            "return_embedding": False,
            "generator": "OllamaChatGenerator",
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "generation_timeout_seconds": GENERATION_TIMEOUT_SECONDS,
            "prompt_template": PROMPT_TEMPLATE,
            "timing_method": "time.perf_counter",
            "warmup_runs": WARMUP_RUNS,
            "measurement_runs": MEASUREMENT_RUNS,
            "retrieval_timing_boundary": (
                "query embedding plus document retrieval"
            ),
            "generation_timing_boundary": (
                "Ollama generator execution only"
            ),
            "execution_time_definition": (
                "mean retrieval time plus mean generation time"
            ),
        },
    )


def get_chunk_id(document):
    """Return a stable identifier for a retrieved Haystack document."""

    if document.id:
        return document.id

    metadata = document.meta or {}
    document_id = metadata.get("document_id")
    chunk_index = metadata.get("chunk_index")

    if document_id is not None and chunk_index is not None:
        return f"{document_id}:{chunk_index}"

    raise ValueError(
        "Retrieved Haystack document has no stable chunk identifier."
    )


def serialize_retrieval(documents):
    """Convert retrieved Haystack documents into the shared chunk format."""

    retrieved_chunks = []

    for rank, document in enumerate(documents, start=1):
        metadata = dict(document.meta or {})

        metadata.setdefault(
            "source",
            "devops-rag-corpus.pdf",
        )

        retrieved_chunks.append(
            {
                "rank": rank,
                "chunk_id": get_chunk_id(document),
                "text": document.content,
                "metadata": metadata,
                "score": document.score,
            }
        )

    return retrieved_chunks


def build_context(retrieved_chunks):
    """Build the generation context from normalized retrieved chunks."""

    context_parts = []

    for chunk in retrieved_chunks:
        text = chunk.get("text")

        if not text:
            continue

        page = (chunk.get("metadata") or {}).get("page")

        context_parts.append(
            f"[Source: devops-rag-corpus.pdf, page {page}]\n{text}"
        )

    if not context_parts:
        raise ValueError("No usable retrieved document content was returned.")

    return "\n\n".join(context_parts)


def build_pipeline_components():
    """Initialize the Haystack embedding, retrieval, and generation components."""

    records = json.loads(
        EMBEDDINGS_PATH.read_text(encoding="utf-8")
    )

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
        embedding_similarity_function=SIMILARITY_FUNCTION
    )
    store.write_documents(documents)

    embedder = SentenceTransformersTextEmbedder(
        model=MODEL_NAME,
        normalize_embeddings=NORMALIZE_EMBEDDINGS,
        device=ComponentDevice.from_single(
            __import__("torch").device(EMBEDDING_DEVICE)
        ),
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
            "temperature": TEMPERATURE,
            "num_predict": MAX_TOKENS,
        },
        timeout=GENERATION_TIMEOUT_SECONDS,
    )

    return embedder, retriever, generator


def retrieve_with_timing(embedder, retriever, question):
    """Measure query embedding and document retrieval with a monotonic clock."""

    start_time = time.perf_counter()

    query_result = embedder.run(text=question)

    retrieval_result = retriever.run(
        query_embedding=query_result["embedding"]
    )

    elapsed = time.perf_counter() - start_time

    return retrieval_result["documents"], elapsed


def generate_with_timing(generator, prompt):
    """Measure only the Ollama generation call."""

    start_time = time.perf_counter()

    response = generator.run(
        messages=[ChatMessage.from_user(prompt)]
    )

    elapsed = time.perf_counter() - start_time

    answer = response["replies"][0].text

    return answer, elapsed


def build_timing_summary(
    retrieval_times,
    generation_times,
    execution_times,
):
    """Calculate mean and median timings from measured repetitions."""

    return {
        "retrieval_mean_seconds": statistics.mean(retrieval_times),
        "retrieval_median_seconds": statistics.median(retrieval_times),
        "generation_mean_seconds": statistics.mean(generation_times),
        "generation_median_seconds": statistics.median(generation_times),
        "execution_mean_seconds": statistics.mean(execution_times),
        "execution_median_seconds": statistics.median(execution_times),
    }


def run_warmup(embedder, retriever, generator, question):
    """Run one complete warm-up without including it in benchmark results."""

    documents, _ = retrieve_with_timing(
        embedder,
        retriever,
        question,
    )

    retrieved_chunks = serialize_retrieval(documents)
    context = build_context(retrieved_chunks)

    prompt = PROMPT_TEMPLATE.format(
        context=context,
        question=question,
    )

    generate_with_timing(generator, prompt)


def main():
    questions = json.loads(
        QUESTIONS_PATH.read_text(encoding="utf-8")
    )

    # Validate the run before loading or modifying existing results.
    current_metadata = create_current_run_metadata()

    run_metadata, run_status = initialize_run(
        metadata_path=RUN_METADATA_PATH,
        results_path=RESULTS_PATH,
        current_metadata=current_metadata,
    )

    print(f"Evaluation run ID: {run_metadata['run_id']}")
    print(f"Run status: {run_status}")

    # Load existing results only after run validation succeeds.
    results = load_results(RESULTS_PATH)

    completed_ids = {
        item["question_id"]
        for item in results
        if item.get("status") == "success"
    }

    pending_questions = [
        item
        for item in questions
        if item["id"] not in completed_ids
    ]

    print(f"Total questions: {len(questions)}")
    print(f"Already completed: {len(completed_ids)}")
    print(f"Remaining: {len(pending_questions)}")

    if not pending_questions:
        print("All questions have already been evaluated.")
        return

    embedder, retriever, generator = build_pipeline_components()

    # One complete warm-up, excluded from all measured timings.
    print("\nRunning one warm-up iteration...")

    run_warmup(
        embedder,
        retriever,
        generator,
        pending_questions[0]["question"],
    )

    print("Warm-up completed. Starting measured evaluations.")

    for index, item in enumerate(pending_questions, start=1):
        question_id = item["id"]
        question = item["question"]

        retrieval_times = []
        generation_times = []
        execution_times = []

        print(
            f"\n[{index}/{len(pending_questions)}] "
            f"Evaluating {question_id}"
        )
        print(question)

        try:
            final_answer = None
            final_retrieved_chunks = None

            for measurement in range(1, MEASUREMENT_RUNS + 1):
                print(
                    f"Measurement {measurement}/{MEASUREMENT_RUNS}..."
                )

                # Retrieval timing includes query embedding and vector search.
                documents, retrieval_elapsed = retrieve_with_timing(
                    embedder,
                    retriever,
                    question,
                )

                retrieved_chunks = serialize_retrieval(documents)

                # Context construction and prompt formatting are excluded
                # from both retrieval and generation timing.
                context = build_context(retrieved_chunks)

                prompt = PROMPT_TEMPLATE.format(
                    context=context,
                    question=question,
                )

                answer, generation_elapsed = generate_with_timing(
                    generator,
                    prompt,
                )

                retrieval_times.append(retrieval_elapsed)
                generation_times.append(generation_elapsed)
                execution_times.append(
                    retrieval_elapsed + generation_elapsed
                )

                # Keep the final measured answer and retrieved chunks.
                final_answer = answer
                final_retrieved_chunks = retrieved_chunks

                print(
                    f"Retrieval: {retrieval_elapsed:.2f}s | "
                    f"Generation: {generation_elapsed:.2f}s"
                )

            timing_summary = build_timing_summary(
                retrieval_times,
                generation_times,
                execution_times,
            )

            average_retrieval = timing_summary[
                "retrieval_mean_seconds"
            ]
            average_generation = timing_summary[
                "generation_mean_seconds"
            ]

            # Execution time is consistently defined as the sum of
            # mean retrieval and mean generation time.
            average_execution = (
                average_retrieval + average_generation
            )

            record = build_result(
                question_id=question_id,
                topic=item.get("topic"),
                question=question,
                expected_answer=item.get("expected_answer"),
                source_section=item.get("source_section"),
                framework=FRAMEWORK_NAME,
                model=LLM_MODEL,
                embedding_model=MODEL_NAME,
                top_k=TOP_K,
                status="success",
                generated_answer=final_answer,
                retrieved_chunks=final_retrieved_chunks,
                retrieval_time_seconds=average_retrieval,
                generation_time_seconds=average_generation,
                execution_time_seconds=average_execution,
                timing_summary=timing_summary,
                warmup_runs=WARMUP_RUNS,
                measurement_runs=MEASUREMENT_RUNS,
            )

            print(f"\n[{index}/{len(pending_questions)}] {question_id}: SUCCESS")
            print(
                f"Average retrieval: {average_retrieval:.2f}s "
                f"(median: {timing_summary['retrieval_median_seconds']:.2f}s)"
            )
            print(
                f"Average generation: {average_generation:.2f}s "
                f"(median: {timing_summary['generation_median_seconds']:.2f}s)"
            )
            print(
                f"Average execution: {average_execution:.2f}s "
                f"(median: {timing_summary['execution_median_seconds']:.2f}s)"
            )

        except Exception as error:
            elapsed = sum(retrieval_times) + sum(generation_times)

            record = build_result(
                question_id=question_id,
                topic=item.get("topic"),
                question=question,
                expected_answer=item.get("expected_answer"),
                source_section=item.get("source_section"),
                framework=FRAMEWORK_NAME,
                model=LLM_MODEL,
                embedding_model=MODEL_NAME,
                top_k=TOP_K,
                status="failed",
                execution_time_seconds=elapsed,
                error=str(error),
            )

            print(f"\n[{index}/{len(pending_questions)}] {question_id}: FAILED")
            print(error)

        # Replace an existing record for this question, if present.
        results = [
            existing for existing in results
            if existing["question_id"] != question_id
        ]
        results.append(record)

        # Save after each question so progress survives interruptions.
        save_results(RESULTS_PATH, results)

    successful = sum(
        1 for result in results
        if result["status"] == "success"
    )
    failed = sum(
        1 for result in results
        if result["status"] == "failed"
    )

    print("\nEvaluation completed.")
    print(f"Run ID: {run_metadata['run_id']}")
    print(f"Run status: {run_status}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Results: {RESULTS_PATH}")
    print(f"Run metadata: {RUN_METADATA_PATH}")


if __name__ == "__main__":
    main()

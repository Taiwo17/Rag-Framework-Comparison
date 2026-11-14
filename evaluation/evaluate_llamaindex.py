
import json
import statistics
import time
from pathlib import Path

from llama_index.core import StorageContext, load_index_from_storage
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.faiss import FaissVectorStore

try:
    from .result_schema import (
        build_result,
        load_results,
        save_results as save_schema_results,
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
        save_results as save_schema_results,
    )
    from run_tracking import (
        build_run_metadata,
        calculate_file_hash,
        initialize_run,
        get_package_version,
    )


BASE_DIR = Path(__file__).resolve().parent.parent

CORPUS_PATH = BASE_DIR / "corpus" / "devops-rag-corpus.pdf"
QUESTIONS_PATH = BASE_DIR / "evaluation" / "questions.json"
INDEX_DIR = BASE_DIR / "evaluation" / "vector_stores" / "llamaindex"

RESULTS_DIR = BASE_DIR / "evaluation" / "results"
OUTPUT_PATH = RESULTS_DIR / "llamaindex-results.json"
RUN_METADATA_PATH = OUTPUT_PATH.with_suffix(".run.json")

FRAMEWORK_NAME = "LlamaIndex"
FRAMEWORK_PACKAGE = "llama-index-core"

OLLAMA_URL = "http://172.27.224.1:11434"
MODEL_NAME = "qwen2.5:3b"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

TOP_K = 4
REQUEST_TIMEOUT = 420
TEMPERATURE = 0
MAX_TOKENS = 500
EMBEDDING_DEVICE = "cpu"
NORMALIZE_EMBEDDINGS = True

WARMUP_RUNS = 1
MEASUREMENT_RUNS = 3


PROMPT_TEMPLATE = """
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


def load_questions():
    return json.loads(
        QUESTIONS_PATH.read_text(encoding="utf-8")
    )


def calculate_index_fingerprint():
    """Fingerprint all files that make up the persisted LlamaIndex index."""

    if not INDEX_DIR.is_dir():
        raise FileNotFoundError(
            f"LlamaIndex index directory not found: {INDEX_DIR}"
        )

    index_files = sorted(
        path for path in INDEX_DIR.rglob("*")
        if path.is_file()
    )

    if not index_files:
        raise FileNotFoundError(
            f"No index files found in: {INDEX_DIR}"
        )

    return {
        str(path.relative_to(INDEX_DIR)): calculate_file_hash(path)
        for path in index_files
    }


def create_current_run_metadata():
    """Build metadata for the current LlamaIndex evaluation configuration."""

    return build_run_metadata(
        framework=FRAMEWORK_NAME,
        package_name=FRAMEWORK_PACKAGE,
        model=MODEL_NAME,
        embedding_model=EMBEDDING_MODEL,
        top_k=TOP_K,
        corpus_path=CORPUS_PATH,
        config={
            "questions_sha256": calculate_file_hash(QUESTIONS_PATH),
            "index_fingerprints": calculate_index_fingerprint(),
            "index_directory": str(INDEX_DIR),
            "ollama_url": OLLAMA_URL,
            "embedding_device": EMBEDDING_DEVICE,
            "normalize_embeddings": NORMALIZE_EMBEDDINGS,
            "retriever": "LlamaIndex index.as_retriever",
            "retrieval_top_k": TOP_K,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "request_timeout_seconds": REQUEST_TIMEOUT,
            "prompt_template": PROMPT_TEMPLATE,
            "huggingface_embedding_package_version": get_package_version(
                "llama-index-embeddings-huggingface"
            ),
            "ollama_package_version": get_package_version(
                "llama-index-llms-ollama"
            ),
            "faiss_package_version": get_package_version(
                "llama-index-vector-stores-faiss"
            ),
            "timing_method": "time.perf_counter",
            "warmup_runs": WARMUP_RUNS,
            "measurement_runs": MEASUREMENT_RUNS,
            "timing_boundaries": {
                "retrieval": "retriever.retrieve",
                "generation": "llm.complete",
                "execution": "retrieval_time + generation_time",
                "excluded": [
                    "context construction",
                    "prompt formatting",
                    "warmup runs",
                ],
            },
        },
    )


def build_prompt(question, context):
    return PROMPT_TEMPLATE.format(
        context=context,
        question=question,
    )


def get_chunk_id(node):
    """Return the persistent LlamaIndex node ID."""

    node_id = getattr(node, "id_", None)

    if node_id:
        return str(node_id)

    metadata = getattr(node, "metadata", {}) or {}

    document_id = metadata.get("document_id")
    chunk_index = metadata.get("chunk_index")

    if document_id is not None and chunk_index is not None:
        return f"{document_id}:{chunk_index}"

    return None


def serialize_retrieval(retrieved_nodes):
    """Convert LlamaIndex retrieval results to the shared chunk format."""

    chunks = []

    for rank, result in enumerate(retrieved_nodes, start=1):
        node = result.node

        chunks.append({
            "rank": rank,
            "chunk_id": get_chunk_id(node),
            "text": node.text,
            "metadata": dict(node.metadata or {}),
            "score": result.score,
        })

    return chunks


def build_context(retrieved_chunks):
    """Build generation context from normalized retrieval records."""

    context_parts = []

    for chunk in retrieved_chunks:
        metadata = chunk.get("metadata") or {}

        source = metadata.get(
            "source",
            "devops-rag-corpus.pdf",
        )
        page = metadata.get("page", "Unknown")
        chunk_id = chunk.get("chunk_id") or "Unknown ID"
        text = chunk.get("text") or ""

        if not text:
            raise ValueError(
                f"Retrieved chunk {chunk_id} has no text."
            )

        context_parts.append(
            f"[Source: {source}, Page: {page}, Chunk: {chunk_id}]\n"
            f"{text}"
        )

    return "\n\n".join(context_parts)


def retrieve_with_timing(retriever, question):
    """Retrieve chunks and measure retrieval duration with a monotonic clock."""

    start_time = time.perf_counter()
    retrieved_nodes = retriever.retrieve(question)
    retrieval_time = time.perf_counter() - start_time

    retrieved_chunks = serialize_retrieval(retrieved_nodes)

    return retrieved_chunks, retrieval_time


def generate_with_timing(llm, prompt):
    """Generate an answer and measure only the LLM call."""

    start_time = time.perf_counter()
    response = llm.complete(prompt)
    generation_time = time.perf_counter() - start_time

    return str(response).strip(), generation_time


def build_timing_summary(
    retrieval_times,
    generation_times,
    execution_times,
):
    """Calculate mean and median timings from measured runs only."""

    if not retrieval_times or not generation_times or not execution_times:
        raise ValueError(
            "Timing summaries require at least one measurement."
        )

    return {
        "retrieval_mean_seconds": statistics.mean(retrieval_times),
        "retrieval_median_seconds": statistics.median(retrieval_times),
        "generation_mean_seconds": statistics.mean(generation_times),
        "generation_median_seconds": statistics.median(generation_times),
        "execution_mean_seconds": statistics.mean(execution_times),
        "execution_median_seconds": statistics.median(execution_times),
    }


def run_warmup(retriever, llm, question):
    """Execute an unmeasured retrieval and generation warm-up."""

    print("Running warm-up...")

    retrieved_chunks, _ = retrieve_with_timing(
        retriever,
        question,
    )

    context = build_context(retrieved_chunks)
    prompt = build_prompt(question, context)

    # Deliberately discard the answer and timing.
    generate_with_timing(llm, prompt)

    print("Warm-up completed. Warm-up timings are excluded from results.")


def main():
    questions = load_questions()

    # Validate the run before loading or modifying existing results.
    current_metadata = create_current_run_metadata()

    run_metadata, run_status = initialize_run(
        metadata_path=RUN_METADATA_PATH,
        results_path=OUTPUT_PATH,
        current_metadata=current_metadata,
    )

    print(f"Evaluation run ID: {run_metadata['run_id']}")
    print(f"Run status: {run_status}")

    # Load existing results only after run validation succeeds.
    results = load_results(OUTPUT_PATH)

    completed_ids = {
        result["question_id"]
        for result in results
        if result.get("status") == "success"
    }

    pending_questions = [
        item for item in questions
        if item["id"] not in completed_ids
    ]

    print(f"Total questions: {len(questions)}")
    print(f"Already completed: {len(completed_ids)}")
    print(f"Remaining: {len(pending_questions)}")
    print(f"Warm-up runs: {WARMUP_RUNS}")
    print(f"Measurement runs per question: {MEASUREMENT_RUNS}")

    if not pending_questions:
        print("All questions have already been evaluated.")
        return

    embed_model = HuggingFaceEmbedding(
        model_name=EMBEDDING_MODEL,
        device=EMBEDDING_DEVICE,
        normalize=NORMALIZE_EMBEDDINGS,
    )

    llm = Ollama(
        model=MODEL_NAME,
        base_url=OLLAMA_URL,
        temperature=TEMPERATURE,
        request_timeout=REQUEST_TIMEOUT,
        additional_kwargs={"num_predict": MAX_TOKENS},
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

    # Warm up once before collecting any measurements.
    # The warm-up is excluded from all question timing summaries.
    if WARMUP_RUNS > 0:
        run_warmup(
            retriever,
            llm,
            pending_questions[0]["question"],
        )

    for position, item in enumerate(pending_questions, start=1):
        question_id = item["id"]
        question = item["question"]

        question_start_time = time.perf_counter()

        print(
            f"\n[{position}/{len(pending_questions)}] "
            f"Evaluating {question_id}"
        )
        print(question)

        retrieval_times = []
        generation_times = []
        execution_times = []

        retrieved_chunks = []
        answer = ""

        try:
            for measurement in range(1, MEASUREMENT_RUNS + 1):
                print(
                    f"Measurement {measurement}/{MEASUREMENT_RUNS}"
                )

                current_chunks, retrieval_time = retrieve_with_timing(
                    retriever,
                    question,
                )

                context = build_context(current_chunks)
                prompt = build_prompt(question, context)

                current_answer, generation_time = generate_with_timing(
                    llm,
                    prompt,
                )

                execution_time = retrieval_time + generation_time

                retrieval_times.append(retrieval_time)
                generation_times.append(generation_time)
                execution_times.append(execution_time)

                # Keep the final measured run's answer and retrieved chunks.
                retrieved_chunks = current_chunks
                answer = current_answer

            timing_summary = build_timing_summary(
                retrieval_times,
                generation_times,
                execution_times,
            )

            execution_mean = timing_summary["execution_mean_seconds"]

            result_record = build_result(
                question_id=question_id,
                topic=item.get("topic"),
                question=question,
                expected_answer=item.get("expected_answer"),
                source_section=item.get("source_section"),
                framework=FRAMEWORK_NAME,
                model=MODEL_NAME,
                embedding_model=EMBEDDING_MODEL,
                top_k=TOP_K,
                status="success",
                generated_answer=answer,
                retrieved_chunks=retrieved_chunks,
                retrieval_time_seconds=timing_summary[
                    "retrieval_mean_seconds"
                ],
                generation_time_seconds=timing_summary[
                    "generation_mean_seconds"
                ],
                execution_time_seconds=execution_mean,
                timing_summary=timing_summary,
                warmup_runs=WARMUP_RUNS,
                measurement_runs=MEASUREMENT_RUNS,
            )

            # Replace any previous record for this question.
            results = [
                record for record in results
                if record["question_id"] != question_id
            ]
            results.append(result_record)

            # Save using the shared result schema.
            save_schema_results(OUTPUT_PATH, results)

            print(f"Answer: {answer}")
            print(f"Retrieved chunks: {len(retrieved_chunks)}")
            print(f"Sources: {result_record['sources']}")
            print(
                "Mean retrieval time: "
                f"{timing_summary['retrieval_mean_seconds']:.2f} seconds"
            )
            print(
                "Mean generation time: "
                f"{timing_summary['generation_mean_seconds']:.2f} seconds"
            )
            print(
                "Mean execution time: "
                f"{execution_mean:.2f} seconds"
            )
            print(
                "Median execution time: "
                f"{timing_summary['execution_median_seconds']:.2f} seconds"
            )
            print("Result saved.")

        except Exception as error:
            elapsed_time = time.perf_counter() - question_start_time

            error_record = build_result(
                question_id=question_id,
                topic=item.get("topic"),
                question=question,
                expected_answer=item.get("expected_answer"),
                source_section=item.get("source_section"),
                framework=FRAMEWORK_NAME,
                model=MODEL_NAME,
                embedding_model=EMBEDDING_MODEL,
                top_k=TOP_K,
                status="failed",
                execution_time_seconds=elapsed_time,
                error=str(error),
            )

            results = [
                record for record in results
                if record["question_id"] != question_id
            ]
            results.append(error_record)

            save_schema_results(OUTPUT_PATH, results)

            print(f"FAILED: {error}")
            print("Failure recorded. Continuing to the next question.")

    successful = sum(
        result.get("status") == "success"
        for result in results
    )

    failed = sum(
        result.get("status") == "failed"
        for result in results
    )

    print("\nEvaluation completed.")
    print(f"Run ID: {run_metadata['run_id']}")
    print(f"Run status: {run_status}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Results: {OUTPUT_PATH}")
    print(f"Run metadata: {RUN_METADATA_PATH}")


if __name__ == "__main__":
    main()

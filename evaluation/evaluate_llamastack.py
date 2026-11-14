
import json
import statistics
import time
import urllib.error
import urllib.request

from pathlib import Path

try:
    from .result_schema import (
        build_result,
        load_results,
        save_results as save_schema_results,
    )
    from .run_tracking import (
        build_run_metadata,
        initialize_run,
        calculate_file_hash,
    )
except ImportError:
    from result_schema import (
        build_result,
        load_results,
        save_results as save_schema_results,
    )
    from run_tracking import (
        build_run_metadata,
        initialize_run,
        calculate_file_hash,
    )


BASE_URL = "http://localhost:8321"
VECTOR_DB_ID = "llamastack_devops_rag"
MODEL_ID = "ollama/qwen2.5:3b"

# This must match the embedding model registered with the LlamaStack
# vector database, not the embedding model used by other frameworks.
EMBEDDING_MODEL = "ollama/all-minilm:l6-v2"

TOP_K = 4
TIMEOUT = 420
TEMPERATURE = 0
MAX_TOKENS = 500

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

BASE_DIR = Path(__file__).resolve().parent.parent
QUESTIONS_PATH = BASE_DIR / "evaluation" / "questions.json"
CORPUS_PATH = BASE_DIR / "corpus" / "devops-rag-corpus.pdf"

OUTPUT_PATH = (
    BASE_DIR / "evaluation" / "results" / "llamastack-results.json"
)
RUN_METADATA_PATH = OUTPUT_PATH.with_suffix(".run.json")


def post_request(endpoint, payload):
    url = f"{BASE_URL}{endpoint}"

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            return json.loads(response.read().decode("utf-8"))

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8")
        raise RuntimeError(
            f"HTTP {error.code}: {error_body}"
        ) from error


def retrieve_chunks(question):
    payload = {
        "vector_db_id": VECTOR_DB_ID,
        "query": question,
        "params": {
            "max_chunks": TOP_K
        },
    }

    result = post_request("/v1/vector-io/query", payload)

    chunks = result.get("chunks", [])
    scores = result.get("scores", [])

    if not chunks:
        raise RuntimeError("No relevant chunks were retrieved.")

    return chunks, scores


def retrieve_with_timing(question):
    """Measure the LlamaStack retrieval API call using a monotonic clock."""

    start_time = time.perf_counter()

    chunks, scores = retrieve_chunks(question)

    elapsed = time.perf_counter() - start_time

    return chunks, scores, elapsed


def get_chunk_id(chunk):
    """Return an existing chunk ID or construct one from stable metadata."""

    chunk_id = chunk.get("chunk_id") or chunk.get("id")

    if chunk_id is not None:
        return str(chunk_id)

    metadata = chunk.get("metadata") or {}

    document_id = metadata.get("document_id")
    chunk_index = metadata.get("chunk_index")

    if document_id is not None and chunk_index is not None:
        return f"{document_id}:{chunk_index}"

    return None


def build_context(chunks):
    context_parts = []

    for chunk in chunks:
        metadata = chunk.get("metadata") or {}

        source = metadata.get("source", "Unknown source")
        page = metadata.get("page", "Unknown page")
        chunk_id = get_chunk_id(chunk) or "Unknown ID"

        content = chunk.get("content") or chunk.get("text") or ""

        if not content:
            raise ValueError(
                f"Retrieved chunk {chunk_id} has no content."
            )

        context_parts.append(
            f"[Source: {source}, Page: {page}, Chunk: {chunk_id}]\n"
            f"{content}"
        )

    return "\n\n".join(context_parts)


def generate_answer(question, context):
    """Construct the prompt and return the generated answer."""

    prompt = PROMPT_TEMPLATE.format(
        context=context,
        question=question,
    )

    payload = {
        "model_id": MODEL_ID,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "sampling_params": {
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
        },
    }

    result = post_request(
        "/v1/inference/chat-completion",
        payload,
    )

    return result["completion_message"]["content"]


def generate_with_timing(question, context):
    """Measure only the LlamaStack generation API call."""

    # Prompt construction is deliberately outside the timed section.
    prompt = PROMPT_TEMPLATE.format(
        context=context,
        question=question,
    )

    payload = {
        "model_id": MODEL_ID,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
        "sampling_params": {
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
        },
    }

    start_time = time.perf_counter()

    result = post_request(
        "/v1/inference/chat-completion",
        payload,
    )

    elapsed = time.perf_counter() - start_time

    answer = result["completion_message"]["content"]

    return answer, elapsed


def serialize_retrieval(chunks, scores):
    """Convert LlamaStack retrieval output to the shared chunk format."""

    retrieved = []

    for index, chunk in enumerate(chunks):
        metadata = chunk.get("metadata") or {}

        content = chunk.get("content") or chunk.get("text")

        score = (
            scores[index]
            if index < len(scores)
            else chunk.get("score")
        )

        retrieved.append({
            "rank": index + 1,
            "chunk_id": get_chunk_id(chunk),
            "text": content,
            "metadata": metadata,
            "score": score,
        })

    return retrieved


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


def run_warmup(question):
    """Run one complete warm-up, excluded from measured timings."""

    chunks, _scores, _retrieval_elapsed = retrieve_with_timing(question)

    context = build_context(chunks)

    generate_with_timing(question, context)


def create_current_run_metadata():
    """Build metadata from the current evaluation configuration."""

    return build_run_metadata(
        framework="LlamaStack",
        package_name="llama-stack",
        model=MODEL_ID,
        embedding_model=EMBEDDING_MODEL,
        top_k=TOP_K,
        corpus_path=CORPUS_PATH,
        config={
            "base_url": BASE_URL,
            "vector_db_id": VECTOR_DB_ID,
            "timeout": TIMEOUT,
            "questions_sha256": calculate_file_hash(QUESTIONS_PATH),
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "prompt_template": PROMPT_TEMPLATE,
            "retrieval_endpoint": "/v1/vector-io/query",
            "generation_endpoint": "/v1/inference/chat-completion",
            "retrieval_parameter": "max_chunks",
            "timing_method": "time.perf_counter",
            "warmup_runs": WARMUP_RUNS,
            "measurement_runs": MEASUREMENT_RUNS,
            "retrieval_timing_boundary": (
                "LlamaStack vector retrieval API call"
            ),
            "generation_timing_boundary": (
                "LlamaStack chat completion API call only"
            ),
            "execution_time_definition": (
                "mean retrieval time plus mean generation time"
            ),
        },
    )


def main():
    questions = json.loads(
        QUESTIONS_PATH.read_text(encoding="utf-8")
    )

    # Build and validate run metadata before loading existing results.
    current_metadata = create_current_run_metadata()

    run_metadata, run_status = initialize_run(
        metadata_path=RUN_METADATA_PATH,
        results_path=OUTPUT_PATH,
        current_metadata=current_metadata,
    )

    print(f"Evaluation run ID: {run_metadata['run_id']}")
    print(f"Run status: {run_status}")

    # Load results only after the run has been validated.
    results = load_results(OUTPUT_PATH)

    completed_ids = {
        item["question_id"]
        for item in results
        if item.get("status") == "success"
    }

    pending_questions = [
        item for item in questions
        if item["id"] not in completed_ids
    ]

    print("=" * 65)
    print("LLAMASTACK BATCH RAG EVALUATION")
    print("=" * 65)
    print(f"Total questions: {len(questions)}")
    print(f"Already completed: {len(completed_ids)}")
    print(f"Remaining: {len(pending_questions)}")
    print(f"Warm-up runs: {WARMUP_RUNS}")
    print(f"Measurement runs per question: {MEASUREMENT_RUNS}")
    print(f"Output: {OUTPUT_PATH}")
    print(f"Run metadata: {RUN_METADATA_PATH}")
    print("=" * 65)

    if not pending_questions:
        print("All questions have already been evaluated.")
        return

    # One complete warm-up before measured questions.
    print("\nRunning one warm-up iteration...", flush=True)

    run_warmup(pending_questions[0]["question"])

    print(
        "Warm-up completed. Starting measured evaluations.",
        flush=True,
    )

    for position, item in enumerate(pending_questions, 1):
        question_id = item["id"]
        question = item["question"]

        retrieval_times = []
        generation_times = []
        execution_times = []

        print(
            f"\n[{position}/{len(pending_questions)}] "
            f"{question_id}: {question}",
            flush=True,
        )

        try:
            final_answer = None
            final_retrieved_chunks = None

            for measurement in range(1, MEASUREMENT_RUNS + 1):
                print(
                    f"Measurement {measurement}/{MEASUREMENT_RUNS}...",
                    flush=True,
                )

                chunks, scores, retrieval_elapsed = (
                    retrieve_with_timing(question)
                )

                retrieved_chunks = serialize_retrieval(chunks, scores)

                # Context construction is excluded from retrieval and
                # generation timing.
                context = build_context(chunks)

                answer, generation_elapsed = generate_with_timing(
                    question,
                    context,
                )

                retrieval_times.append(retrieval_elapsed)
                generation_times.append(generation_elapsed)

                execution_times.append(
                    retrieval_elapsed + generation_elapsed
                )

                # Retain the final measured answer and retrieved chunks.
                final_answer = answer
                final_retrieved_chunks = retrieved_chunks

                print(
                    f"Retrieval: {retrieval_elapsed:.2f}s | "
                    f"Generation: {generation_elapsed:.2f}s",
                    flush=True,
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

            # Consistent execution-time definition across frameworks.
            average_execution = (
                average_retrieval + average_generation
            )

            record = build_result(
                question_id=question_id,
                topic=item.get("topic"),
                question=question,
                expected_answer=item.get("expected_answer"),
                source_section=item.get("source_section"),
                framework="LlamaStack",
                model=MODEL_ID,
                embedding_model=EMBEDDING_MODEL,
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

            print(
                f"Completed {question_id}.",
                flush=True,
            )
            print(
                f"Average retrieval: {average_retrieval:.2f}s "
                f"(median: "
                f"{timing_summary['retrieval_median_seconds']:.2f}s)",
                flush=True,
            )
            print(
                f"Average generation: {average_generation:.2f}s "
                f"(median: "
                f"{timing_summary['generation_median_seconds']:.2f}s)",
                flush=True,
            )
            print(
                f"Average execution: {average_execution:.2f}s "
                f"(median: "
                f"{timing_summary['execution_median_seconds']:.2f}s)",
                flush=True,
            )

        except Exception as error:
            elapsed = sum(retrieval_times) + sum(generation_times)

            record = build_result(
                question_id=question_id,
                topic=item.get("topic"),
                question=question,
                expected_answer=item.get("expected_answer"),
                source_section=item.get("source_section"),
                framework="LlamaStack",
                model=MODEL_ID,
                embedding_model=EMBEDDING_MODEL,
                top_k=TOP_K,
                status="failed",
                execution_time_seconds=elapsed,
                error=str(error),
            )

            print(
                f"FAILED: {error}",
                flush=True,
            )

        # Replace any previous record for this question.
        results = [
            result for result in results
            if result["question_id"] != question_id
        ]

        results.append(record)

        # Save after every question to preserve progress.
        save_schema_results(OUTPUT_PATH, results)

        print(
            f"Progress saved: {len(completed_ids) + position} "
            f"of {len(questions)} questions.",
            flush=True,
        )

    successful = sum(
        1 for result in results
        if result.get("status") == "success"
    )

    failed = sum(
        1 for result in results
        if result.get("status") == "failed"
    )

    print("\n" + "=" * 65)
    print("EVALUATION SUMMARY")
    print("=" * 65)
    print(f"Total questions: {len(questions)}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Results saved to: {OUTPUT_PATH}")
    print(f"Run ID: {run_metadata['run_id']}")
    print("=" * 65)


if __name__ == "__main__":
    main()

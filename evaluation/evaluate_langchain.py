
import json
import statistics
import time
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama

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
    )


BASE_DIR = Path(__file__).resolve().parent.parent

QUESTIONS_PATH = BASE_DIR / "evaluation" / "questions.json"
CORPUS_PATH = BASE_DIR / "corpus" / "devops-rag-corpus.pdf"

INDEX_DIR = BASE_DIR / "evaluation" / "vector_stores" / "langchain"

RESULTS_DIR = BASE_DIR / "evaluation" / "results"
RESULTS_PATH = RESULTS_DIR / "langchain-results.json"
RUN_METADATA_PATH = RESULTS_PATH.with_suffix(".run.json")

FRAMEWORK_NAME = "LangChain"
FRAMEWORK_PACKAGE = "langchain"

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
OLLAMA_MODEL = "qwen2.5:3b"
OLLAMA_URL = "http://172.27.224.1:11434"

TOP_K = 4
TEMPERATURE = 0
MAX_TOKENS = 500
GENERATION_TIMEOUT_SECONDS = 420
EMBEDDING_DEVICE = "cpu"
NORMALIZE_EMBEDDINGS = True

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


def load_questions():
    return json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))


def calculate_index_fingerprint():
    """Fingerprint all files that make up the local FAISS index."""

    if not INDEX_DIR.is_dir():
        raise FileNotFoundError(
            f"LangChain FAISS index directory not found: {INDEX_DIR}"
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
    """Build metadata for the current LangChain evaluation configuration."""

    return build_run_metadata(
        framework=FRAMEWORK_NAME,
        package_name=FRAMEWORK_PACKAGE,
        model=OLLAMA_MODEL,
        embedding_model=MODEL_NAME,
        top_k=TOP_K,
        corpus_path=CORPUS_PATH,
        config={
            "questions_sha256": calculate_file_hash(QUESTIONS_PATH),
            "index_fingerprints": calculate_index_fingerprint(),
            "index_directory": str(INDEX_DIR),
            "ollama_url": OLLAMA_URL,
            "embedding_device": EMBEDDING_DEVICE,
            "normalize_embeddings": NORMALIZE_EMBEDDINGS,
            "temperature": TEMPERATURE,
            "max_tokens": MAX_TOKENS,
            "generation_timeout_seconds": GENERATION_TIMEOUT_SECONDS,
            "prompt_template": PROMPT_TEMPLATE,
            "retrieval_method": "similarity_search_with_score",
            "retrieval_top_k": TOP_K,
            "warmup_runs": WARMUP_RUNS,
            "measurement_runs": MEASUREMENT_RUNS,
            "timing_method": "time.perf_counter",
            "timing_boundaries": {
                "retrieval": "similarity_search_with_score",
                "generation": "llm.invoke",
                "execution": "retrieval_time_plus_generation_time",
            },
        },
    )


def get_chunk_id(document):
    """Return a stable identifier for a retrieved LangChain document."""

    if document.id:
        return document.id

    metadata = document.metadata or {}

    document_id = metadata.get("document_id")
    chunk_index = metadata.get("chunk_index")

    if document_id is not None and chunk_index is not None:
        return f"{document_id}:{chunk_index}"

    raise ValueError(
        "Retrieved LangChain document has no stable chunk identifier."
    )


def serialize_retrieval(retrieved_documents):
    """Convert LangChain retrieval results into the shared chunk format."""

    retrieved_chunks = []

    for rank, (document, score) in enumerate(
        retrieved_documents,
        start=1,
    ):
        metadata = dict(document.metadata or {})

        metadata.setdefault(
            "source",
            "devops-rag-corpus.pdf",
        )

        retrieved_chunks.append(
            {
                "rank": rank,
                "chunk_id": get_chunk_id(document),
                "text": document.page_content,
                "metadata": metadata,
                "score": float(score),
            }
        )

    return retrieved_chunks


def build_context(retrieved_chunks):
    """Build generation context from normalized retrieved chunks."""

    context_parts = []

    for chunk in retrieved_chunks:
        text = chunk.get("text")

        if not text:
            continue

        metadata = chunk.get("metadata") or {}
        source = metadata.get(
            "source",
            "devops-rag-corpus.pdf",
        )
        page = metadata.get("page")

        context_parts.append(
            f"[Source: {source}, page {page}]\n{text}"
        )

    if not context_parts:
        raise ValueError(
            "No usable retrieved document content was returned."
        )

    return "\n\n".join(context_parts)


def build_prompt(context, question):
    return PROMPT_TEMPLATE.format(
        context=context,
        question=question,
    )


def retrieve_with_timing(vector_store, question):
    """Retrieve documents and measure retrieval time independently."""

    start_time = time.perf_counter()

    retrieved_documents = vector_store.similarity_search_with_score(
        question,
        k=TOP_K,
    )

    retrieval_time = time.perf_counter() - start_time

    retrieved_chunks = serialize_retrieval(retrieved_documents)

    return retrieved_chunks, retrieval_time


def generate_with_timing(llm, prompt):
    """Generate an answer and measure only the LLM invocation."""

    start_time = time.perf_counter()

    response = llm.invoke(prompt)

    generation_time = time.perf_counter() - start_time

    return response.content, generation_time


def summarize_measurements(values):
    """Return mean and median for a list of measured durations."""

    if not values:
        raise ValueError("Cannot summarize an empty timing measurement list.")

    return {
        "mean_seconds": statistics.mean(values),
        "median_seconds": statistics.median(values),
    }


def build_timing_summary(
    retrieval_times,
    generation_times,
    execution_times,
):
    """Build the shared timing summary from measured runs only."""

    return {
        "retrieval_mean_seconds": statistics.mean(retrieval_times),
        "retrieval_median_seconds": statistics.median(retrieval_times),
        "generation_mean_seconds": statistics.mean(generation_times),
        "generation_median_seconds": statistics.median(generation_times),
        "execution_mean_seconds": statistics.mean(execution_times),
        "execution_median_seconds": statistics.median(execution_times),
    }


def run_warmup(vector_store, llm, question):
    """
    Execute an unmeasured retrieval and generation run.

    Warm-up measurements are deliberately excluded from reported statistics.
    """

    print("\nRunning warm-up...")
    retrieved_chunks, _ = retrieve_with_timing(
        vector_store,
        question,
    )

    context = build_context(retrieved_chunks)
    prompt = build_prompt(context, question)

    generate_with_timing(llm, prompt)

    print("Warm-up completed. Its timings will not enter benchmark results.")


def evaluate_question(vector_store, llm, item):
    """Run repeated retrieval and generation measurements for one question."""

    question_id = item["id"]
    question = item["question"]

    retrieval_times = []
    generation_times = []
    execution_times = []

    final_answer = None
    final_retrieved_chunks = None

    for measurement in range(1, MEASUREMENT_RUNS + 1):
        print(
            f"Measurement {measurement}/{MEASUREMENT_RUNS} "
            f"for {question_id}"
        )

        retrieved_chunks, retrieval_time = retrieve_with_timing(
            vector_store,
            question,
        )

        context = build_context(retrieved_chunks)
        prompt = build_prompt(context, question)

        answer, generation_time = generate_with_timing(
            llm,
            prompt,
        )

        execution_time = retrieval_time + generation_time

        retrieval_times.append(retrieval_time)
        generation_times.append(generation_time)
        execution_times.append(execution_time)

        final_answer = answer
        final_retrieved_chunks = retrieved_chunks

        print(f"Retrieval: {retrieval_time:.2f} seconds")
        print(f"Generation: {generation_time:.2f} seconds")
        print(f"Total measured time: {execution_time:.2f} seconds")

    timing_summary = build_timing_summary(
        retrieval_times,
        generation_times,
        execution_times,
    )

    return {
        "answer": final_answer,
        "retrieved_chunks": final_retrieved_chunks,
        "retrieval_time_seconds": timing_summary[
            "retrieval_mean_seconds"
        ],
        "generation_time_seconds": timing_summary[
            "generation_mean_seconds"
        ],
        "execution_time_seconds": timing_summary[
            "execution_mean_seconds"
        ],
        "timing_summary": timing_summary,
    }


def main():
    questions = load_questions()

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
        result["question_id"]
        for result in results
        if result.get("status") == "success"
    }

    pending_questions = [
        question
        for question in questions
        if question["id"] not in completed_ids
    ]

    print(f"Total questions: {len(questions)}")
    print(f"Already completed: {len(completed_ids)}")
    print(f"Remaining: {len(pending_questions)}")
    print(f"Warm-up runs: {WARMUP_RUNS}")
    print(f"Measurements per question: {MEASUREMENT_RUNS}")

    if not pending_questions:
        print("All questions have already been evaluated.")
        return

    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": EMBEDDING_DEVICE},
        encode_kwargs={
            "normalize_embeddings": NORMALIZE_EMBEDDINGS
        },
    )

    vector_store = FAISS.load_local(
        str(INDEX_DIR),
        embeddings,
        allow_dangerous_deserialization=True,
    )

    llm = ChatOllama(
        model=OLLAMA_MODEL,
        base_url=OLLAMA_URL,
        temperature=TEMPERATURE,
        num_predict=MAX_TOKENS,
        client_kwargs={
            "timeout": GENERATION_TIMEOUT_SECONDS
        },
    )

    warmup_completed = False

    for index, item in enumerate(pending_questions, start=1):
        question_id = item["id"]
        question = item["question"]

        print("\n" + "=" * 60)
        print(f"Question {index}/{len(pending_questions)}: {question_id}")
        print(question)

        try:
            if not warmup_completed and WARMUP_RUNS > 0:
                for _ in range(WARMUP_RUNS):
                    run_warmup(
                        vector_store,
                        llm,
                        question,
                    )

                warmup_completed = True

            measurement_result = evaluate_question(
                vector_store,
                llm,
                item,
            )

            timing_summary = measurement_result["timing_summary"]

            record = build_result(
                question_id=question_id,
                topic=item.get("topic"),
                question=question,
                expected_answer=item.get("expected_answer"),
                source_section=item.get("source_section"),
                framework=FRAMEWORK_NAME,
                model=OLLAMA_MODEL,
                embedding_model=MODEL_NAME,
                top_k=TOP_K,
                status="success",
                generated_answer=measurement_result["answer"],
                retrieved_chunks=measurement_result["retrieved_chunks"],
                retrieval_time_seconds=measurement_result[
                    "retrieval_time_seconds"
                ],
                generation_time_seconds=measurement_result[
                    "generation_time_seconds"
                ],
                execution_time_seconds=measurement_result[
                    "execution_time_seconds"
                ],
                timing_summary=timing_summary,
                warmup_runs=WARMUP_RUNS,
                measurement_runs=MEASUREMENT_RUNS,
            )

            print(f"\nAnswer: {measurement_result['answer']}")
            print(
                "Retrieved chunks: "
                f"{len(measurement_result['retrieved_chunks'])}"
            )
            print(
                "Mean retrieval time: "
                f"{timing_summary['retrieval_mean_seconds']:.2f} seconds"
            )
            print(
                "Median retrieval time: "
                f"{timing_summary['retrieval_median_seconds']:.2f} seconds"
            )
            print(
                "Mean generation time: "
                f"{timing_summary['generation_mean_seconds']:.2f} seconds"
            )
            print(
                "Median generation time: "
                f"{timing_summary['generation_median_seconds']:.2f} seconds"
            )
            print(
                "Mean total execution time: "
                f"{timing_summary['execution_mean_seconds']:.2f} seconds"
            )
            print(
                "Median total execution time: "
                f"{timing_summary['execution_median_seconds']:.2f} seconds"
            )

        except Exception as error:
            record = build_result(
                question_id=question_id,
                topic=item.get("topic"),
                question=question,
                expected_answer=item.get("expected_answer"),
                source_section=item.get("source_section"),
                framework=FRAMEWORK_NAME,
                model=OLLAMA_MODEL,
                embedding_model=MODEL_NAME,
                top_k=TOP_K,
                status="failed",
                warmup_runs=WARMUP_RUNS,
                measurement_runs=MEASUREMENT_RUNS,
                error=str(error),
            )

            print(f"\nFailed: {error}")

        # Replace any previous record for this question.
        results = [
            existing for existing in results
            if existing["question_id"] != question_id
        ]
        results.append(record)

        # Persist progress after every question.
        save_schema_results(RESULTS_PATH, results)

        print(f"Saved progress for {question_id}.")

    successful = sum(
        1 for result in results
        if result.get("status") == "success"
    )

    failed = sum(
        1 for result in results
        if result.get("status") == "failed"
    )

    print("\n" + "=" * 60)
    print("LANGCHAIN EVALUATION COMPLETED")
    print("=" * 60)
    print(f"Run ID: {run_metadata['run_id']}")
    print(f"Run status: {run_status}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Results: {RESULTS_PATH}")
    print(f"Run metadata: {RUN_METADATA_PATH}")


if __name__ == "__main__":
    main()

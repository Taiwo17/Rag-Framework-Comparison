
import json
from pathlib import Path


RESULT_FIELDS = (
    "question_id",
    "topic",
    "question",
    "expected_answer",
    "source_section",
    "framework",
    "model",
    "embedding_model",
    "top_k",
    "status",
    "generated_answer",
    "retrieved_chunks",
    "sources",
    "retrieval_count",
    "retrieval_time_seconds",
    "generation_time_seconds",
    "execution_time_seconds",
    "timing_summary",
    "warmup_runs",
    "measurement_runs",
    "error",
)


TIMING_SUMMARY_FIELDS = (
    "retrieval_mean_seconds",
    "retrieval_median_seconds",
    "generation_mean_seconds",
    "generation_median_seconds",
    "execution_mean_seconds",
    "execution_median_seconds",
)


def normalize_chunk(chunk, rank):
    """Convert framework-specific chunk records into the shared format."""

    metadata = dict(chunk.get("metadata") or {})

    if "page" in chunk and "page" not in metadata:
        metadata["page"] = chunk["page"]

    return {
        "rank": chunk.get("rank", rank),
        "chunk_id": chunk.get(
            "chunk_id",
            chunk.get("id"),
        ),
        "text": chunk.get(
            "text",
            chunk.get("content"),
        ),
        "metadata": metadata,
        "score": chunk.get("score"),
    }


def extract_sources(chunks):
    """Build a consistent source and page representation."""

    source_pages = {}

    for chunk in chunks:
        metadata = chunk.get("metadata") or {}

        source = metadata.get(
            "source",
            "devops-rag-corpus.pdf",
        )
        page = metadata.get("page")

        source_pages.setdefault(source, set())

        if page is not None:
            source_pages[source].add(page)

    return [
        {
            "source": source,
            "pages": sorted(pages, key=str),
        }
        for source, pages in sorted(source_pages.items())
    ]


def normalize_timing_summary(summary):
    """
    Normalize timing summaries into the shared flat format.

    Supports:
    1. Current flat format from all four evaluators.
    2. Legacy nested retrieval/generation/total format.
    """

    if not isinstance(summary, dict):
        return None

    # Current evaluator format.
    if any(field in summary for field in TIMING_SUMMARY_FIELDS):
        return {
            field: summary.get(field)
            for field in TIMING_SUMMARY_FIELDS
        }

    # Backward compatibility with the older nested format.
    normalized = {}

    for metric in ("retrieval", "generation", "total"):
        values = summary.get(metric)

        if not isinstance(values, dict):
            values = {}

        output_metric = (
            "execution" if metric == "total" else metric
        )

        normalized[f"{output_metric}_mean_seconds"] = (
            values.get("mean_seconds")
        )
        normalized[f"{output_metric}_median_seconds"] = (
            values.get("median_seconds")
        )

    return normalized


def normalize_result(record):
    """Convert an existing result record to the shared schema."""

    question_id = record.get(
        "question_id",
        record.get("id"),
    )

    chunks = [
        normalize_chunk(chunk, rank)
        for rank, chunk in enumerate(
            record.get("retrieved_chunks") or [],
            start=1,
        )
    ]

    return {
        "question_id": question_id,
        "topic": record.get("topic"),
        "question": record.get("question"),
        "expected_answer": record.get("expected_answer"),
        "source_section": record.get("source_section"),
        "framework": record.get("framework"),
        "model": record.get("model"),
        "embedding_model": record.get("embedding_model"),
        "top_k": record.get("top_k"),
        "status": record.get("status", "failed"),
        "generated_answer": (
            record.get("generated_answer")
            or record.get("answer")
        ),
        "retrieved_chunks": chunks,
        "sources": extract_sources(chunks),
        "retrieval_count": len(chunks),
        "retrieval_time_seconds": record.get(
            "retrieval_time_seconds"
        ),
        "generation_time_seconds": record.get(
            "generation_time_seconds"
        ),
        "execution_time_seconds": record.get(
            "execution_time_seconds",
            0,
        ),
        "timing_summary": normalize_timing_summary(
            record.get("timing_summary")
        ),
        "warmup_runs": record.get("warmup_runs", 0),
        "measurement_runs": record.get("measurement_runs", 1),
        "error": record.get("error"),
    }


def build_result(
    *,
    question_id,
    topic=None,
    question=None,
    expected_answer=None,
    source_section=None,
    framework=None,
    model=None,
    embedding_model=None,
    top_k=None,
    status="failed",
    generated_answer=None,
    retrieved_chunks=None,
    retrieval_time_seconds=None,
    generation_time_seconds=None,
    execution_time_seconds=0,
    timing_summary=None,
    warmup_runs=0,
    measurement_runs=1,
    error=None,
):
    """Build a result using the shared schema."""

    chunks = [
        normalize_chunk(chunk, rank)
        for rank, chunk in enumerate(
            retrieved_chunks or [],
            start=1,
        )
    ]

    return {
        "question_id": question_id,
        "topic": topic,
        "question": question,
        "expected_answer": expected_answer,
        "source_section": source_section,
        "framework": framework,
        "model": model,
        "embedding_model": embedding_model,
        "top_k": top_k,
        "status": status,
        "generated_answer": generated_answer,
        "retrieved_chunks": chunks,
        "sources": extract_sources(chunks),
        "retrieval_count": len(chunks),
        "retrieval_time_seconds": (
            round(retrieval_time_seconds, 2)
            if retrieval_time_seconds is not None
            else None
        ),
        "generation_time_seconds": (
            round(generation_time_seconds, 2)
            if generation_time_seconds is not None
            else None
        ),
        "execution_time_seconds": round(
            execution_time_seconds,
            2,
        ),
        "timing_summary": normalize_timing_summary(
            timing_summary
        ),
        "warmup_runs": warmup_runs,
        "measurement_runs": measurement_runs,
        "error": error,
    }


def load_results(path):
    """Load existing results and normalize legacy records."""

    path = Path(path)

    if not path.exists():
        return []

    records = json.loads(path.read_text(encoding="utf-8"))

    return [
        normalize_result(record)
        for record in records
    ]


def save_results(path, results):
    """Save normalized results in a consistent JSON format."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    normalized = [
        normalize_result(record)
        for record in results
    ]

    path.write_text(
        json.dumps(
            normalized,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

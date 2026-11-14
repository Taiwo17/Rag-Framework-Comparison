
import hashlib
import json
import uuid

from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


TRACKED_FIELDS = (
    "framework",
    "framework_version",
    "model",
    "embedding_model",
    "top_k",
    "corpus_sha256",
    "config_sha256",
)


def calculate_file_hash(path):
    """Return a SHA-256 fingerprint for a file."""

    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Fingerprint source not found: {path}"
        )

    digest = hashlib.sha256()

    with path.open("rb") as file:
        for block in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(block)

    return digest.hexdigest()


def calculate_config_hash(config):
    """Return a stable SHA-256 fingerprint for configuration data."""

    serialized = json.dumps(
        config,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def get_package_version(package_name):
    """Return the installed package version."""

    try:
        return version(package_name)
    except PackageNotFoundError:
        return "not-installed"


def build_run_metadata(
    *,
    framework,
    package_name,
    model,
    embedding_model,
    top_k,
    corpus_path,
    config,
):
    """Create metadata describing an evaluation configuration."""

    return {
        "run_id": str(uuid.uuid4()),
        "started_at": datetime.now(timezone.utc).isoformat(),
        "framework": framework,
        "framework_version": get_package_version(package_name),
        "model": model,
        "embedding_model": embedding_model,
        "top_k": top_k,
        "corpus_sha256": calculate_file_hash(corpus_path),
        "config_sha256": calculate_config_hash(config),
    }


def load_run_metadata(path):
    """Load previously saved run metadata."""

    path = Path(path)

    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8"))


def save_run_metadata(path, metadata):
    """Persist run metadata."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def validate_run_metadata(existing, current):
    """Reject resume when tracked evaluation settings have changed."""

    if existing is None:
        raise ValueError("Previous run metadata does not exist.")

    differences = [
        field
        for field in TRACKED_FIELDS
        if existing.get(field) != current.get(field)
    ]

    if differences:
        raise ValueError(
            "Evaluation configuration has changed. "
            "Existing results cannot be resumed. "
            f"Changed fields: {', '.join(differences)}. "
            "Archive the old results and metadata before starting "
            "a new evaluation run."
        )

    return True


def initialize_run(metadata_path, results_path, current_metadata):
    """
    Initialize a new tracked run or safely resume a matching run.

    Existing result files without metadata are treated as legacy results.
    They are never automatically adopted or overwritten.
    """

    metadata_path = Path(metadata_path)
    results_path = Path(results_path)

    existing_metadata = load_run_metadata(metadata_path)

    if existing_metadata is None:
        if results_path.exists():
            raise ValueError(
                f"Existing results file has no run metadata: {results_path}. "
                "These are untracked legacy results. Archive the results "
                "file before starting a new tracked run."
            )

        save_run_metadata(metadata_path, current_metadata)

        return current_metadata, "new"

    if not results_path.exists():
        raise ValueError(
            "Run metadata exists but its results file is missing. "
            "Restore the results file or archive the metadata before "
            "starting a new run."
        )

    validate_run_metadata(existing_metadata, current_metadata)

    return existing_metadata, "resumed"

from pathlib import Path

from evaluation.result_schema import load_results


RESULTS_DIR = Path("evaluation/results")

FRAMEWORKS = {
    "LlamaStack": "llamastack-results.json",
    "LlamaIndex": "llamaindex-results.json",
    "Haystack": "haystack-results.json",
    "LangChain": "langchain-results.json",
}


def load_framework_results(filename):
    """Load framework results using the shared result schema."""

    path = RESULTS_DIR / filename

    if not path.exists():
        print(f"WARNING: Results file not found: {path}")
        return {}

    records = load_results(path)

    return {
        record["question_id"]: record
        for record in records
        if record.get("question_id") is not None
    }


def question_sort_key(question_id):
    """Sort question IDs numerically, such as Q1, Q2, Q10."""

    value = str(question_id)

    if value.startswith("Q") and value[1:].isdigit():
        return (0, int(value[1:]))

    return (1, value)


def get_source_pages(record):
    """Extract unique page numbers from the normalized sources field."""

    pages = {
        str(page)
        for source in record.get("sources", [])
        for page in source.get("pages", [])
        if page is not None
    }

    if not pages:
        return "Not recorded"

    sorted_pages = sorted(
        pages,
        key=lambda page: (
            0,
            int(page),
        ) if page.isdigit() else (
            1,
            page,
        ),
    )

    return ", ".join(sorted_pages)


results = {
    name: load_framework_results(filename)
    for name, filename in FRAMEWORKS.items()
}

# Use LlamaStack as the reference framework for the question list,
# preserving the original review-generation behaviour.
question_ids = sorted(
    results["LlamaStack"].keys(),
    key=question_sort_key,
)

lines = [
    "# RAG Framework Answer Quality Review",
    "",
    "This document contains the expected answers, generated answers,",
    "and retrieved source pages for all four frameworks.",
    "",
    "Scoring criteria:",
    "- Correctness: 0–2",
    "- Completeness: 0–2",
    "- Context grounding: 0–2",
    "- Relevance: 0–2",
    "- Maximum score: 8 per question",
    "",
    "---",
]

for question_id in question_ids:
    reference = results["LlamaStack"][question_id]

    lines.extend([
        "",
        f"## {question_id}: {reference.get('topic') or 'Topic not recorded'}",
        "",
        f"**Question:** {reference.get('question') or 'Not recorded'}",
        "",
        (
            "**Expected answer:** "
            f"{reference.get('expected_answer') or 'Not recorded'}"
        ),
        "",
    ])

    for framework in FRAMEWORKS:
        record = results[framework].get(question_id)

        lines.extend([
            f"### {framework}",
            "",
        ])

        if record is None:
            lines.extend([
                "No result recorded for this question.",
                "",
            ])
            continue

        answer = (
            record.get("generated_answer")
            or "No answer recorded."
        )

        source_pages = get_source_pages(record)

        lines.extend([
            f"**Retrieved source pages:** {source_pages}",
            "",
            answer,
            "",
        ])

    lines.append("---")

output_path = RESULTS_DIR / "answer-quality-review.md"
output_path.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print(f"Review document created: {output_path}")
print(f"Questions included: {len(question_ids)}")
print(f"Frameworks compared: {len(FRAMEWORKS)}")
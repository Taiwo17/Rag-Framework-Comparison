
import json
from pathlib import Path

RESULTS_DIR = Path("evaluation/results")

FRAMEWORKS = {
    "LlamaStack": "llamastack-results.json",
    "LlamaIndex": "llamaindex-results.json",
    "Haystack": "haystack-results.json",
    "LangChain": "langchain-results.json",
}


def load_results(filename):
    path = RESULTS_DIR / filename
    records = json.loads(path.read_text(encoding="utf-8"))
    return {
        record.get("question_id", record.get("id")): record
        for record in records
    }


results = {
    name: load_results(filename)
    for name, filename in FRAMEWORKS.items()
}

question_ids = sorted(
    results["LlamaStack"].keys(),
    key=lambda value: int(value.replace("Q", ""))
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
        f"## {question_id}: {reference['topic']}",
        "",
        f"**Question:** {reference['question']}",
        "",
        f"**Expected answer:** {reference['expected_answer']}",
        "",
    ])

    for framework in FRAMEWORKS:
        record = results[framework][question_id]

        answer = (
            record.get("generated_answer")
            or record.get("answer")
            or "No answer recorded."
        )

        chunks = record.get("retrieved_chunks", [])

        pages = []
        for chunk in chunks:
            metadata = chunk.get("metadata") or {}
            page = chunk.get("page", metadata.get("page"))

            if page is not None:
                pages.append(str(page))

        source_pages = ", ".join(sorted(set(pages), key=int)) or "Not recorded"

        lines.extend([
            f"### {framework}",
            "",
            f"**Retrieved source pages:** {source_pages}",
            "",
            answer,
            "",
        ])

    lines.append("---")

output_path = RESULTS_DIR / "answer-quality-review.md"
output_path.write_text("\n".join(lines), encoding="utf-8")

print(f"Review document created: {output_path}")
print(f"Questions included: {len(question_ids)}")
print(f"Frameworks compared: {len(FRAMEWORKS)}")

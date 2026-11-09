from pypdf import PdfReader
from pathlib import Path
import hashlib

pdf_path = Path("corpus/devops-rag-corpus.pdf")

if not pdf_path.exists():
    raise FileNotFoundError(f"PDF not found: {pdf_path}")

reader = PdfReader(str(pdf_path))

print(f"Total pages: {len(reader.pages)}")

for index, page in enumerate(reader.pages, start=1):
    page_text = page.extract_text() or ""

    print(f"\nPage {index}")
    print(f"Extracted characters: {len(page_text.strip())}")
    print(f"Preview: {page_text.strip()[:150]}")

    if len(page_text.strip()) < 100:
        print("WARNING: Very little extractable text on this page.")

sha256 = hashlib.sha256(pdf_path.read_bytes()).hexdigest()

print(f"\nSHA-256: {sha256}")
print("\nCorpus verification completed.")
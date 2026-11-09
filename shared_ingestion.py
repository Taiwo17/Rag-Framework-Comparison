import json
from pathlib import Path

from pypdf import PdfReader
from transformers import AutoTokenizer


BASE_DIR = Path(__file__).resolve().parent

PDF_PATH = BASE_DIR / "corpus" / "devops-rag-corpus.pdf"
OUTPUT_PATH = BASE_DIR / "evaluation" / "shared_chunks.json"
CONFIG_PATH = BASE_DIR / "configs" / "rag-config.json"


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)

def extract_pages(pdf_path):
    reader = PdfReader(str(pdf_path))

    pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""

        if text.strip():
            pages.append({
                "page": page_number,
                "text": text.strip()
            })

    return pages

def create_chunks(pages, tokenizer, chunk_size, overlap):
    chunks = []
    chunk_id = 1

    for page in pages:
        text = page["text"]

        token_ids = tokenizer.encode(text, add_special_tokens=False)

        start = 0

        while start < len(token_ids):
            end  = start + chunk_size

            chunk_tokens = token_ids[start:end]

            chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True, clean_up_tokenization_spaces=False)

            if chunk_text.strip():
                chunks.append({
                    "id": f"chunk-{chunk_id:04d}",
                    "text": chunk_text.strip(),
                    "metadata": {
                        "source": PDF_PATH.name,
                        "page": page["page"],
                        "chunk_index": chunk_id,
                    },
                })
                chunk_id += 1

            if end >= len(token_ids):
                break
            start = end - overlap
    
    return chunks

def main():
    if not PDF_PATH.exists(): 
        raise FileNotFoundError(f"PDF not Found: {PDF_PATH}")

    config = load_config()

    chunk_size = config["chunking"]["size"]
    overlap = config["chunking"]["overlap"]
    embedding_model = config["embeddings"]["model"]

    if overlap >= chunk_size:
        raise ValueError("Chunk overlap must be  smaller than chunk size")
    
    print("Loading embedding tokenizer...")

    tokenizer = AutoTokenizer.from_pretrained(embedding_model)

    print("Extracting PDF pages...")

    pages = extract_pages(PDF_PATH)

    print(f"Extracted {len(pages)} pages.")

    print("Creating shared chunks")

    chunks = create_chunks(pages, tokenizer, chunk_size, overlap)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as file:
        json.dump(chunks, file, indent=4, ensure_ascii=False)

    print("\nIngestion completed successfully.")
    print(f"Total pages processed: {len(pages)}")
    print(f"Total chunks created: {len(chunks)}")
    print(f"Chunk size: {chunk_size} tokens")
    print(f"Chunk overlap: {overlap} tokens")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
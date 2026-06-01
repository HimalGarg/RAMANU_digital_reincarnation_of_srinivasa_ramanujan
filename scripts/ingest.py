"""
scripts/ingest.py — Data Ingestion Pipeline
=============================================
Processes raw PDF and TXT files into chunked documents for embedding.
Outputs JSON Lines files to data/processed/.
"""

import argparse
import json
import os
import re
import sys

from langchain_text_splitters import RecursiveCharacterTextSplitter


def clean_text(text: str) -> str:
    """
    Clean raw text: normalize whitespace, fix hyphenation,
    strip page numbers and headers.
    """
    # Fix hyphenated line breaks (e.g., "mathe-\nmatics" → "mathematics")
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

    # Normalize multiple newlines to double newline (paragraph breaks)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Normalize whitespace within lines
    text = re.sub(r"[ \t]+", " ", text)

    # Strip common page number patterns
    text = re.sub(r"\n\s*\d+\s*\n", "\n", text)
    text = re.sub(r"\n\s*-\s*\d+\s*-\s*\n", "\n", text)

    return text.strip()


def detect_document_type(text: str, filename: str) -> str:
    """
    Detect the type of document based on content and filename.

    Returns: "letter", "notebook", or "biography"
    """
    lower_text = text[:500].lower()
    lower_name = filename.lower()

    if any(kw in lower_name for kw in ["letter", "correspondence"]):
        return "letter"
    if any(kw in lower_name for kw in ["notebook", "notes"]):
        return "notebook"
    if any(kw in lower_name for kw in ["biography", "life", "history"]):
        return "biography"

    # Content-based detection
    if any(kw in lower_text for kw in ["dear sir", "dear hardy", "beg to"]):
        return "letter"
    if any(kw in lower_text for kw in ["theorem", "identity", "formula", "series"]):
        return "notebook"

    return "biography"


def process_txt_file(filepath: str) -> str:
    """Read and clean a TXT file."""
    with open(filepath, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return clean_text(text)


def process_pdf_file(filepath: str) -> str:
    """Extract text from a PDF file using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        print(f"  [!] pdfplumber not installed, skipping PDF: {filepath}")
        return ""

    text_parts = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    return clean_text("\n\n".join(text_parts))


def chunk_text(
    text: str,
    source_name: str,
    doc_type: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[dict]:
    """
    Split text into chunks using RecursiveCharacterTextSplitter.

    Returns list of dicts: {"id", "text", "metadata"}
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks = splitter.split_text(text)

    # Build structured output
    base_id = re.sub(r"[^a-zA-Z0-9]", "_", source_name).lower()
    documents = []
    for idx, chunk in enumerate(chunks):
        doc = {
            "id": f"{base_id}_chunk_{idx:04d}",
            "text": chunk.strip(),
            "metadata": {
                "source": source_name,
                "chunk_index": idx,
                "type": doc_type,
                "total_chunks": len(chunks),
            },
        }
        documents.append(doc)

    return documents


def ingest_file(filepath: str) -> list[dict]:
    """
    Ingest a single file: extract text, detect type, chunk.

    Returns list of chunk dicts.
    """
    filename = os.path.basename(filepath)
    ext = os.path.splitext(filepath)[1].lower()

    if ext == ".txt":
        text = process_txt_file(filepath)
    elif ext == ".pdf":
        text = process_pdf_file(filepath)
    else:
        print(f"  [!] Unsupported file type: {filepath}")
        return []

    if not text:
        print(f"  [!] No text extracted from: {filepath}")
        return []

    doc_type = detect_document_type(text, filename)
    chunks = chunk_text(text, filename, doc_type)

    return chunks


def main():
    parser = argparse.ArgumentParser(
        description="Ingest raw documents into chunked JSON Lines format."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to a file or directory of files to ingest.",
    )
    parser.add_argument(
        "--output",
        default="data/processed/",
        help="Output directory for processed JSON Lines files.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=512,
        help="Maximum chunk size in characters (default: 512).",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=64,
        help="Overlap between chunks in characters (default: 64).",
    )

    args = parser.parse_args()

    # Collect input files
    input_path = os.path.abspath(args.input)
    if os.path.isfile(input_path):
        files = [input_path]
    elif os.path.isdir(input_path):
        files = []
        for root, _, filenames in os.walk(input_path):
            for fn in sorted(filenames):
                if fn.endswith((".txt", ".pdf")):
                    files.append(os.path.join(root, fn))
    else:
        print(f"Error: {input_path} does not exist.")
        sys.exit(1)

    if not files:
        print("No .txt or .pdf files found.")
        sys.exit(1)

    print(f"\n[*] Ingesting {len(files)} file(s)...\n")

    # Ensure output directory exists
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    total_chunks = 0
    total_files = 0

    for filepath in files:
        filename = os.path.basename(filepath)
        print(f"  Processing: {filename}")

        chunks = ingest_file(filepath)
        if not chunks:
            continue

        # Write chunks to JSONL file
        output_filename = os.path.splitext(filename)[0] + ".jsonl"
        output_path = os.path.join(output_dir, output_filename)

        with open(output_path, "w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

        print(f"    -> {len(chunks)} chunks -> {output_filename}")
        total_chunks += len(chunks)
        total_files += 1

    print(f"\n[OK] Done! {total_files} file(s) processed, {total_chunks} total chunks created.")
    print(f"     Output directory: {output_dir}\n")


if __name__ == "__main__":
    main()

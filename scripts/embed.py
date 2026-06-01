"""
scripts/embed.py — Embedding Pipeline
=======================================
Loads processed chunks from data/processed/ and embeds them into ChromaDB
using the RAG pipeline.
"""

import json
import os
import sys

# Add project root to path so we can import the agent package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tqdm import tqdm
from agent.rag import RAGPipeline


def load_jsonl_files(processed_dir: str) -> list[dict]:
    """
    Load all JSONL files from the processed directory.

    Args:
        processed_dir: Path to the directory containing .jsonl files.

    Returns:
        List of document dicts with "id", "text", "metadata".
    """
    documents = []
    processed_dir = os.path.abspath(processed_dir)

    if not os.path.exists(processed_dir):
        print(f"Error: Directory {processed_dir} does not exist.")
        return []

    jsonl_files = sorted(
        f for f in os.listdir(processed_dir) if f.endswith(".jsonl")
    )

    if not jsonl_files:
        print(f"No .jsonl files found in {processed_dir}")
        return []

    for filename in jsonl_files:
        filepath = os.path.join(processed_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        doc = json.loads(line)
                        documents.append(doc)
                    except json.JSONDecodeError as e:
                        print(f"  [!] Skipping malformed line in {filename}: {e}")

    return documents


def main():
    processed_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "processed")
    )

    print("\n=== Ramanujan Knowledge Embedding Pipeline ===")
    print("=" * 50)

    # Load documents
    print(f"\n[*] Loading documents from: {processed_dir}")
    documents = load_jsonl_files(processed_dir)

    if not documents:
        print("[ERROR] No documents to embed. Run ingest.py first.")
        sys.exit(1)

    print(f"   Found {len(documents)} chunks to embed.\n")

    # Initialize RAG pipeline
    print("[*] Initializing RAG pipeline...")
    rag = RAGPipeline()

    # Check for already-embedded documents (idempotent)
    stats_before = rag.get_collection_stats()
    existing_count = stats_before["total_documents"]

    if existing_count > 0:
        print(f"   Collection already has {existing_count} documents.")
        # Get existing IDs to skip duplicates
        try:
            existing = rag._collection.get(limit=existing_count)
            existing_ids = set(existing["ids"]) if existing["ids"] else set()
        except Exception:
            existing_ids = set()

        # Filter out already-embedded documents
        new_docs = [d for d in documents if d["id"] not in existing_ids]
        if not new_docs:
            print("   [OK] All documents already embedded. Nothing to do.\n")
            _print_stats(rag)
            return
        print(f"   Skipping {len(documents) - len(new_docs)} already-embedded documents.")
        documents = new_docs

    # Embed documents in batches
    print(f"\n[*] Embedding {len(documents)} documents into ChromaDB...\n")
    rag.add_documents(documents)

    # Print final stats
    print()
    _print_stats(rag)


def _print_stats(rag: RAGPipeline):
    """Print ChromaDB collection statistics."""
    stats = rag.get_collection_stats()
    print("=" * 50)
    print("[*] ChromaDB Statistics:")
    print(f"    Collection: {stats['collection_name']}")
    print(f"    Total documents: {stats['total_documents']}")
    print("=" * 50)
    print()


if __name__ == "__main__":
    main()

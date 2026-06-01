"""
tests/test_rag.py — RAG Pipeline Tests
========================================
"""

import os
import shutil
import sys
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from agent.rag import RAGPipeline


# Use a single temporary directory for all tests, but unique collections
TEST_VECTORDB_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "tmp_test_vectordb"
)


def _make_rag() -> RAGPipeline:
    """Create a RAGPipeline with a unique collection name to avoid conflicts."""
    unique_name = f"test_{uuid.uuid4().hex[:8]}"
    return RAGPipeline(
        persist_dir=TEST_VECTORDB_DIR,
        collection_name=unique_name,
    )


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db_after_all():
    """Clean up test vectordb directory after all tests complete."""
    yield
    # Try to clean up; ignore errors on Windows if files are still locked
    try:
        if os.path.exists(TEST_VECTORDB_DIR):
            shutil.rmtree(TEST_VECTORDB_DIR, ignore_errors=True)
    except Exception:
        pass


def test_embed_returns_vector():
    """Check embedding is a list of floats with correct dimensionality."""
    rag = _make_rag()
    vector = rag.embed_text("The partition function p(5) equals 7.")

    assert isinstance(vector, list)
    assert len(vector) > 0
    assert all(isinstance(v, float) for v in vector)
    # all-MiniLM-L6-v2 produces 384-dimensional vectors
    assert len(vector) == 384


def test_add_and_retrieve():
    """Add 3 documents, query, check results returned."""
    rag = _make_rag()

    docs = [
        {
            "id": "doc_001",
            "text": "The partition function p(n) counts the number of ways to write n as a sum of positive integers.",
            "metadata": {"source": "notebook", "type": "notebook"},
        },
        {
            "id": "doc_002",
            "text": "Ramanujan discovered that 1729 is the smallest number expressible as the sum of two cubes in two different ways.",
            "metadata": {"source": "biography", "type": "biography"},
        },
        {
            "id": "doc_003",
            "text": "The Rogers-Ramanujan identities relate certain infinite series to infinite products.",
            "metadata": {"source": "notebook", "type": "notebook"},
        },
    ]

    rag.add_documents(docs)

    # Verify documents are stored
    stats = rag.get_collection_stats()
    assert stats["total_documents"] == 3

    # Query for partition-related content
    results = rag.retrieve("partition function", n_results=3)
    assert len(results) > 0
    assert any("partition" in r["text"].lower() for r in results)


def test_format_context_truncation():
    """Verify format_context respects the ~2000 token limit."""
    rag = _make_rag()

    # Create results with very long text
    long_text = "Mathematics is beautiful. " * 500  # ~2000 words
    results = [
        {"text": long_text, "metadata": {"source": "test_notebook.txt", "type": "notebook"}},
        {"text": long_text, "metadata": {"source": "test_letter.txt", "type": "letter"}},
    ]

    formatted = rag.format_context(results)

    # The formatted context should be truncated
    # It should end with "..." if truncated
    assert len(formatted) < len(long_text) * 2 + 200
    if len(long_text) * 2 > 8000:
        assert formatted.endswith("...")


def test_metadata_labels():
    """Verify source labels appear in formatted context."""
    rag = _make_rag()

    results = [
        {
            "text": "A result about partitions.",
            "metadata": {"source": "Notebook II", "type": "notebook"},
        },
        {
            "text": "Dear Hardy, I write to you...",
            "metadata": {"source": "Letter, 1913", "type": "letter"},
        },
        {
            "text": "Ramanujan grew up in Kumbakonam.",
            "metadata": {"source": "Kanigel biography", "type": "biography"},
        },
    ]

    formatted = rag.format_context(results)

    assert "Notebook" in formatted
    assert "letter" in formatted.lower()
    assert "Biographical" in formatted or "biography" in formatted.lower()


def test_empty_retrieve():
    """Verify retrieve returns empty list on empty collection."""
    rag = _make_rag()
    results = rag.retrieve("anything at all")
    assert results == []


def test_collection_stats():
    """Verify get_collection_stats returns correct structure."""
    rag = _make_rag()
    stats = rag.get_collection_stats()

    assert "total_documents" in stats
    assert "collection_name" in stats
    assert stats["total_documents"] == 0

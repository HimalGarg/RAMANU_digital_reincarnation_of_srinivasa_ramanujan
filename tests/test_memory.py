"""
tests/test_memory.py — Memory System Tests
============================================
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.memory import ShortTermMemory, LongTermMemory


@pytest.fixture(autouse=True)
def mock_chromadb():
    """Mock ChromaDB client and embedding function for all tests to run fast and isolated."""
    with patch("agent.memory.chromadb.PersistentClient") as mock_client_cls, \
         patch("agent.memory.embedding_functions.SentenceTransformerEmbeddingFunction") as mock_emb_fn_cls:
        
        mock_client = MagicMock()
        mock_collection = MagicMock()
        
        # Configure count default return value
        mock_collection.count.return_value = 0
        
        mock_client_cls.return_value = mock_client
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_emb_fn_cls.return_value = MagicMock()
        
        yield {
            "client": mock_client,
            "collection": mock_collection,
        }


# ─── Short-Term Memory Tests ─────────────────────────────────────────────────


def test_short_term_add_and_get():
    """Add turns and retrieve history as formatted string."""
    stm = ShortTermMemory()
    stm.add_turn("user", "What is a partition?")
    stm.add_turn("ramanujan", "A partition of n is a way of writing n as a sum.")

    history = stm.get_history()
    assert "What is a partition?" in history
    assert "A partition of n" in history
    assert stm.turn_count == 2


def test_short_term_max_turns():
    """Add 15 turns, verify only 10 are returned by default."""
    stm = ShortTermMemory()
    for i in range(15):
        stm.add_turn("user", f"Message {i}")

    history = stm.get_history(max_turns=10)
    # Should contain messages 5-14 (last 10), not 0-4
    assert "Message 14" in history
    assert "Message 5" in history
    assert "Message 4" not in history


def test_short_term_clear():
    """Verify clear wipes all turns."""
    stm = ShortTermMemory()
    stm.add_turn("user", "Hello")
    stm.add_turn("ramanujan", "Namaskaram")
    stm.clear()
    assert stm.turn_count == 0
    assert stm.get_history() == ""


def test_short_term_token_count():
    """Verify token count is a reasonable approximation."""
    stm = ShortTermMemory()
    stm.add_turn("user", "a" * 400)  # ~100 tokens
    count = stm.token_count()
    assert count == 100  # 400 chars // 4


# ─── Long-Term Memory Tests ──────────────────────────────────────────────────


def test_long_term_persist():
    """Save memory, reload from file, check value preserved."""
    # Use a temp file
    fd, tmppath = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    try:
        # Write
        ltm1 = LongTermMemory(filepath=tmppath)
        ltm1.update("favorite_topic", "partition theory")
        ltm1.save()

        # Reload
        ltm2 = LongTermMemory(filepath=tmppath)
        assert ltm2.get("favorite_topic") == "partition theory"
    finally:
        os.unlink(tmppath)


def test_long_term_keyword_match():
    """Store entry, query with matching keyword, verify match."""
    fd, tmppath = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    try:
        ltm = LongTermMemory(filepath=tmppath)
        ltm.update("topics_discussed", "partition theory and infinite series")
        ltm.update("user_math_level", "advanced")

        result = ltm.get_relevant_memories("partition")
        assert "partition" in result.lower() or "Topics Discussed" in result
    finally:
        os.unlink(tmppath)


def test_long_term_summarize():
    """Verify summarize returns non-empty string when entries exist."""
    fd, tmppath = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    try:
        ltm = LongTermMemory(filepath=tmppath)
        ltm.update("test_key", "test_value")
        summary = ltm.summarize()
        assert "1 entries" in summary or "Test Key" in summary
        assert len(summary) > 10
    finally:
        os.unlink(tmppath)


def test_long_term_empty():
    """Verify behavior with no stored memories."""
    fd, tmppath = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    try:
        # Remove the file so we start fresh
        os.unlink(tmppath)
        ltm = LongTermMemory(filepath=tmppath)
        assert ltm.get("nonexistent") is None
        assert ltm.get_relevant_memories("anything") == ""
        assert "No long-term memories" in ltm.summarize()
    finally:
        if os.path.exists(tmppath):
            os.unlink(tmppath)


def test_long_term_add_vector_memory():
    """Verify add_vector_memory correctly calls ChromaDB's add method."""
    fd, tmppath = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    try:
        ltm = LongTermMemory(filepath=tmppath)
        
        # Verify empty string or whitespace does not add anything
        ltm.add_vector_memory("   ")
        assert ltm._collection.add.call_count == 0
        
        # Add normal memory
        ltm.add_vector_memory("User's name is Amit")
        assert ltm._collection.add.call_count == 1
        
        # Verify args
        args, kwargs = ltm._collection.add.call_args
        assert len(kwargs["ids"]) == 1
        assert kwargs["documents"] == ["User's name is Amit"]
        assert "timestamp" in kwargs["metadatas"][0]
    finally:
        os.unlink(tmppath)


def test_long_term_retrieve_vector_memories():
    """Verify retrieve_vector_memories queries ChromaDB when count > 0."""
    fd, tmppath = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    try:
        ltm = LongTermMemory(filepath=tmppath)
        
        # 1. When count is 0
        ltm._collection.count.return_value = 0
        results = ltm.retrieve_vector_memories("who am i?")
        assert results == []
        assert ltm._collection.query.call_count == 0
        
        # 2. When count is > 0
        ltm._collection.count.return_value = 5
        ltm._collection.query.return_value = {
            "documents": [["User's name is Amit", "User lives in Delhi"]]
        }
        
        results = ltm.retrieve_vector_memories("name", n_results=3)
        assert results == ["User's name is Amit", "User lives in Delhi"]
        ltm._collection.query.assert_called_once_with(
            query_texts=["name"],
            n_results=3
        )
    finally:
        os.unlink(tmppath)


def test_long_term_retrieve_vector_memories_exception():
    """Verify retrieve_vector_memories handles exceptions gracefully."""
    fd, tmppath = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    try:
        ltm = LongTermMemory(filepath=tmppath)
        ltm._collection.count.return_value = 1
        ltm._collection.query.side_effect = Exception("ChromaDB error")
        
        results = ltm.retrieve_vector_memories("query")
        assert results == []
    finally:
        os.unlink(tmppath)

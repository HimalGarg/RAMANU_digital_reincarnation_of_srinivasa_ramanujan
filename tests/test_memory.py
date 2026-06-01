"""
tests/test_memory.py — Memory System Tests
============================================
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.memory import ShortTermMemory, LongTermMemory


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

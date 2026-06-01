"""
tests/test_persona.py — Persona Engine Tests
==============================================
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.persona import (
    SCIENTIST_NAME,
    BIRTH_YEAR,
    DEATH_YEAR,
    KNOWLEDGE_CUTOFF_YEAR,
    PERSONA_VERSION,
    SIGNATURE_TOPICS,
    SYSTEM_PROMPT_TEMPLATE,
    build_system_prompt,
)


def test_scientist_name():
    """Verify SCIENTIST_NAME is exactly 'Srinivasa Ramanujan'."""
    assert SCIENTIST_NAME == "Srinivasa Ramanujan"


def test_knowledge_cutoff_constant():
    """Verify KNOWLEDGE_CUTOFF_YEAR == 1920."""
    assert KNOWLEDGE_CUTOFF_YEAR == 1920
    assert BIRTH_YEAR == 1887
    assert DEATH_YEAR == 1920


def test_signature_topics_list():
    """Verify SIGNATURE_TOPICS is a non-empty list of strings."""
    assert isinstance(SIGNATURE_TOPICS, list)
    assert len(SIGNATURE_TOPICS) > 0
    assert all(isinstance(topic, str) for topic in SIGNATURE_TOPICS)
    # Check some expected topics
    topics_lower = [t.lower() for t in SIGNATURE_TOPICS]
    assert "partition theory" in topics_lower
    assert "infinite series" in topics_lower
    assert "continued fractions" in topics_lower


def test_system_prompt_has_placeholders():
    """Verify the template contains all three injection placeholders."""
    assert "{retrieved_context}" in SYSTEM_PROMPT_TEMPLATE
    assert "{conversation_history}" in SYSTEM_PROMPT_TEMPLATE
    assert "{long_term_memory}" in SYSTEM_PROMPT_TEMPLATE


def test_build_system_prompt_fills_placeholders():
    """Verify build_system_prompt fills all placeholders correctly."""
    prompt = build_system_prompt(
        retrieved_context="TEST_CONTEXT",
        conversation_history="TEST_HISTORY",
        long_term_memory="TEST_MEMORY",
    )
    assert "TEST_CONTEXT" in prompt
    assert "TEST_HISTORY" in prompt
    assert "TEST_MEMORY" in prompt
    # Placeholders should no longer be present
    assert "{retrieved_context}" not in prompt
    assert "{conversation_history}" not in prompt
    assert "{long_term_memory}" not in prompt


def test_build_system_prompt_defaults():
    """Verify build_system_prompt handles empty inputs gracefully."""
    prompt = build_system_prompt()
    assert "No specific notebook entries" in prompt
    assert "beginning of our conversation" in prompt
    assert "not spoken before" in prompt


def test_persona_version():
    """Verify PERSONA_VERSION is a non-empty string."""
    assert isinstance(PERSONA_VERSION, str)
    assert len(PERSONA_VERSION) > 0

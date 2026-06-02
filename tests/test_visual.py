"""
tests/test_visual.py — Tests for the Visual Engine
===================================================
Verifies the parsing of visual payloads from the persona response,
the stripping of JSON-visual blocks, and the scene parameter binding.
"""

import json
from unittest.mock import MagicMock
import pytest

from agent.twin import RamanujanTwin
from scripts.render_visual import ContinuedFractionScene, PartitionGridScene, Taxicab3DScene

def test_twin_extracts_visual_payload():
    """Verify that RamanujanTwin parses, sets, and strips the json-visual block."""
    twin = RamanujanTwin(verbose=False)
    
    raw_llm_response = (
        "I have constructed the continued fraction for you:\n\n"
        "```json-visual\n"
        "{\n"
        "  \"visualization_type\": \"continued_fraction\",\n"
        "  \"parameters\": {\n"
        "    \"title\": \"Rogers-Ramanujan\",\n"
        "    \"terms\": [1, 1, 1, 1]\n"
        "  }\n"
        "}\n"
        "```\n\n"
        "Observe how the terms are all unified."
    )
    
    mock_response = MagicMock()
    mock_response.text = raw_llm_response
    twin._model.generate_content = MagicMock(return_value=mock_response)
    
    # Run twin.think
    response_text = twin.think("show me the continued fraction")
    
    # The JSON payload should be stripped from the clean output response
    assert "```json-visual" not in response_text
    assert "I have constructed the continued fraction" in response_text
    assert "Observe how the terms are all unified." in response_text
    
    # Last visual payload must be set correctly
    assert twin.last_visual_payload is not None
    assert twin.last_visual_payload["visualization_type"] == "continued_fraction"
    assert twin.last_visual_payload["parameters"]["title"] == "Rogers-Ramanujan"
    assert twin.last_visual_payload["parameters"]["terms"] == [1, 1, 1, 1]


def test_twin_handles_malformed_json_gracefully():
    """Verify that a malformed json-visual block does not crash the twin."""
    twin = RamanujanTwin(verbose=False)
    
    raw_llm_response = (
        "Here is the representation:\n\n"
        "```json-visual\n"
        "{\n"
        "  \"visualization_type\": \"continued_fraction\",\n"
        "  \"parameters\": {\n"
        "    \"title\": \"Broken JSON\",\n"
        "    \"terms\": [1, 2,\n"  # Malformed JSON
        "  }\n"
        "}\n"
        "```"
    )
    
    mock_response = MagicMock()
    mock_response.text = raw_llm_response
    twin._model.generate_content = MagicMock(return_value=mock_response)
    
    # Should not raise exception
    response_text = twin.think("visualize continued fraction")
    
    # The malformed block should remain or be handled gracefully without crashing
    assert "Here is the representation" in response_text
    assert twin.last_visual_payload is None


def test_manim_scenes_parameter_binding():
    """Verify that parameters are correctly parsed by the Manim scene classes."""
    # Continued Fraction Scene
    cf_scene = ContinuedFractionScene(terms=[1, 3, 5], title="Mock Fraction")
    assert cf_scene.terms == [1, 3, 5]
    assert cf_scene.title_text == "Mock Fraction"

    # Partition Grid Scene
    pg_scene = PartitionGridScene(n=6, partitions=[[4, 2], [3, 3]])
    assert pg_scene.n == 6
    assert pg_scene.partitions == [[4, 2], [3, 3]]

    # Taxicab 3D Scene
    tc_scene = Taxicab3DScene(n=1729, pairs=[[9, 10], [1, 12]])
    assert tc_scene.n == 1729
    assert tc_scene.pairs == [[9, 10], [1, 12]]

"""
Digital Twin of Srinivasa Ramanujan — Agent Package
====================================================
Core modules for the Ramanujan AI persona engine.
"""

from .persona import SCIENTIST_NAME, PERSONA_VERSION, KNOWLEDGE_CUTOFF_YEAR
from .twin import RamanujanTwin

__all__ = ["RamanujanTwin", "SCIENTIST_NAME", "PERSONA_VERSION", "KNOWLEDGE_CUTOFF_YEAR"]

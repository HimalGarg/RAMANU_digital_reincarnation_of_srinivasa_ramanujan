"""
agent/memory.py — Memory System
=================================
Short-term (session) and long-term (cross-session) memory management
for the Ramanujan Digital Twin.
"""

import json
import os
from datetime import datetime, timezone
import uuid
import chromadb
from chromadb.utils import embedding_functions


class ShortTermMemory:
    """
    Session-scoped conversation memory.

    Stores conversation turns for the current session as a list of dicts.
    Cleared on session reset or application exit.
    """

    def __init__(self):
        self._turns: list[dict] = []

    def add_turn(self, role: str, content: str) -> None:
        """
        Add a conversation turn.

        Args:
            role: Either "user" or "ramanujan".
            content: The message content.
        """
        self._turns.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def get_history(self, max_turns: int = 10) -> str:
        """
        Get recent conversation history as a formatted string.

        Args:
            max_turns: Maximum number of turns to return.

        Returns:
            Formatted conversation history string.
        """
        recent = self._turns[-max_turns:] if self._turns else []

        if not recent:
            return ""

        lines = []
        for turn in recent:
            speaker = "You" if turn["role"] == "user" else "Ramanujan"
            lines.append(f"{speaker}: {turn['content']}")

        return "\n\n".join(lines)

    def clear(self) -> None:
        """Wipe all session memory."""
        self._turns.clear()

    def token_count(self) -> int:
        """
        Approximate token count of current history.

        Uses the rough heuristic of 1 token ≈ 4 characters.

        Returns:
            Estimated token count.
        """
        total_chars = sum(len(turn["content"]) for turn in self._turns)
        return total_chars // 4

    @property
    def turn_count(self) -> int:
        """Number of turns in current session."""
        return len(self._turns)


class LongTermMemory:
    """
    Persistent cross-session memory.

    Stores information about the user and conversation themes that persist
    across sessions, saved as a JSON file.

    Tracks: topics explored, mathematical questions asked, moments of wonder
    Ramanujan noted, and the user's apparent math level.
    """

    def __init__(self, filepath: str = "vectordb/long_term.json"):
        """
        Initialize long-term memory, loading from disk if available.

        Args:
            filepath: Path to the JSON persistence file.
        """
        self._filepath = os.path.abspath(filepath)
        self._memories: dict = {}
        self.load()

        # Initialize ChromaDB persistent client for semantic memories
        db_path = os.path.dirname(self._filepath)
        self._chroma_client = chromadb.PersistentClient(path=db_path)
        self._emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self._collection = self._chroma_client.get_or_create_collection(
            name="ramanujan_memories",
            embedding_function=self._emb_fn
        )

    def update(self, key: str, value) -> None:
        """
        Upsert a memory entry with a timestamp.

        Args:
            key: Memory key (e.g., "user_math_level", "topics_discussed").
            value: The value to store (any JSON-serializable type).
        """
        self._memories[key] = {
            "value": value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.save()

    def get(self, key: str):
        """
        Retrieve a memory entry's value.

        Args:
            key: The memory key to look up.

        Returns:
            The stored value, or None if not found.
        """
        entry = self._memories.get(key)
        return entry["value"] if entry else None

    def get_relevant_memories(self, query: str) -> str:
        """
        Find memories relevant to a query using keyword matching.

        Matches query words against memory keys and string values.

        Args:
            query: The search query.

        Returns:
            Formatted string of top 3 relevant memories.
        """
        if not self._memories:
            return ""

        query_words = set(query.lower().split())
        scored = []

        for key, entry in self._memories.items():
            # Score by keyword overlap in key and value
            key_words = set(key.lower().replace("_", " ").split())
            value_str = str(entry["value"]).lower()
            value_words = set(value_str.split())

            # Count matching words
            score = len(query_words & key_words) + len(query_words & value_words)
            if score > 0:
                scored.append((score, key, entry))

        # Sort by score descending, take top 3
        scored.sort(key=lambda x: x[0], reverse=True)
        top = scored[:3]

        if not top:
            return ""

        lines = []
        for _, key, entry in top:
            display_key = key.replace("_", " ").title()
            lines.append(f"- {display_key}: {entry['value']}")

        return "\n".join(lines)

    def summarize(self) -> str:
        """
        Return a brief summary of all stored memories.

        Returns:
            Human-readable summary string.
        """
        if not self._memories:
            return "No long-term memories stored yet."

        lines = [f"Long-term memory ({len(self._memories)} entries):"]
        for key, entry in self._memories.items():
            display_key = key.replace("_", " ").title()
            value_preview = str(entry["value"])
            if len(value_preview) > 80:
                value_preview = value_preview[:77] + "..."
            lines.append(f"  • {display_key}: {value_preview}")

        return "\n".join(lines)

    def save(self) -> None:
        """Write memories to JSON file."""
        os.makedirs(os.path.dirname(self._filepath), exist_ok=True)
        with open(self._filepath, "w", encoding="utf-8") as f:
            json.dump(self._memories, f, indent=2, ensure_ascii=False)

    def load(self) -> None:
        """Load memories from JSON file if it exists."""
        if os.path.exists(self._filepath):
            try:
                with open(self._filepath, "r", encoding="utf-8") as f:
                    self._memories = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._memories = {}

    @property
    def entry_count(self) -> int:
        """Number of memory entries."""
        return len(self._memories)

    def add_vector_memory(self, memory_text: str) -> None:
        """
        Embed and save a user-specific semantic memory fact.

        Args:
            memory_text: Singular user fact to persist (e.g. "User's name is Amit").
        """
        if not memory_text or not memory_text.strip():
            return
        self._collection.add(
            ids=[str(uuid.uuid4())],
            documents=[memory_text.strip()],
            metadatas=[{"timestamp": datetime.now(timezone.utc).isoformat()}]
        )

    def retrieve_vector_memories(self, query: str, n_results: int = 3) -> list[str]:
        """
        Search for semantically relevant user memories.

        Args:
            query: The search text query (e.g. user prompt).
            n_results: Max number of memories to return.

        Returns:
            List of matching memory documents.
        """
        if self._collection.count() == 0:
            return []
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=min(n_results, self._collection.count())
            )
            return results.get("documents", [[]])[0]
        except Exception:
            return []

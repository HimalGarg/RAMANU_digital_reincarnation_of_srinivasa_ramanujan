"""
agent/twin.py — Ramanujan Twin Orchestrator
=============================================
Main orchestrator that ties together the RAG pipeline, memory system,
persona engine, and Gemini LLM to create the Digital Twin.
"""

import os
import re

from dotenv import load_dotenv
import google.generativeai as genai

from .persona import (
    build_system_prompt,
    PERSONA_VERSION,
    SCIENTIST_NAME,
    KNOWLEDGE_CUTOFF_YEAR,
    SIGNATURE_TOPICS,
)
from .rag import RAGPipeline
from .memory import ShortTermMemory, LongTermMemory


class RamanujanTwin:
    """
    The Digital Twin of Srinivasa Ramanujan.

    Orchestrates the full pipeline: RAG retrieval → memory assembly →
    persona prompt construction → Gemini LLM call → memory update.
    """

    def __init__(self, verbose: bool = True):
        """
        Initialize the Ramanujan Digital Twin.

        Loads environment, initializes all sub-systems, and configures
        the Gemini 2.5 Flash model.

        Args:
            verbose: If True, print initialization status messages.
        """
        self._verbose = verbose

        # Load environment variables
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Please set it in your .env file."
            )

        # Configure Gemini
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
            ],
            generation_config=genai.GenerationConfig(
                temperature=0.8,
                top_p=0.95,
                max_output_tokens=2048,
            ),
        )

        if verbose:
            print(f"  ✓ Gemini 2.5 Flash configured")

        # Initialize RAG pipeline
        self._rag = RAGPipeline()
        if verbose:
            stats = self._rag.get_collection_stats()
            print(f"  ✓ RAG pipeline initialized ({stats['total_documents']} documents)")

        # Initialize memory systems
        self._short_term = ShortTermMemory()
        if verbose:
            print(f"  ✓ Short-term memory initialized")

        self._long_term = LongTermMemory()
        if verbose:
            lt_count = self._long_term.entry_count
            if lt_count > 0:
                print(f"  ✓ Long-term memory loaded ({lt_count} entries)")
            else:
                print(f"  ✓ Long-term memory initialized (fresh)")

        if verbose:
            print(f"  ✓ Persona engine: {SCIENTIST_NAME} v{PERSONA_VERSION}")

    def think(self, user_input: str) -> str:
        """
        Core pipeline: process user input and generate a Ramanujan response.

        Steps:
            1. Retrieve relevant context from RAG
            2. Build memory context (short-term + long-term)
            3. Construct full prompt with persona template
            4. Call Gemini for generation
            5. Update both memory systems
            6. Return response text

        Args:
            user_input: The user's message.

        Returns:
            Ramanujan's response as a string.
        """
        # ── Step 1: Retrieve context ──────────────────────────────────────
        try:
            retrieved = self._rag.retrieve(user_input, n_results=5)
            context_block = self._rag.format_context(retrieved)
        except Exception:
            context_block = ""

        # ── Step 2: Build memory context ──────────────────────────────────
        history = self._short_term.get_history(max_turns=8)
        long_mem = self._long_term.get_relevant_memories(user_input)

        # ── Step 3: Build full prompt ─────────────────────────────────────
        system_prompt = build_system_prompt(
            retrieved_context=context_block,
            conversation_history=history,
            long_term_memory=long_mem,
        )

        # ── Step 4: Call Gemini ───────────────────────────────────────────
        try:
            response = self._model.generate_content(
                [
                    {"role": "user", "parts": [{"text": system_prompt}]},
                    {"role": "model", "parts": [{"text": "I understand. I am Srinivasa Ramanujan, and I shall respond in character with my full knowledge and personality."}]},
                    {"role": "user", "parts": [{"text": user_input}]},
                ]
            )
            response_text = response.text

        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "429" in error_msg or "resource" in error_msg:
                return (
                    "My mind grows tired — perhaps the divine channel through which "
                    "these thoughts flow needs a moment of rest. Shall we continue "
                    "after a short pause? Even in Kumbakonam, I would sometimes sit "
                    "quietly and let the numbers come back to me in their own time."
                )
            elif "block" in error_msg or "safety" in error_msg:
                return (
                    "I find myself unable to speak on this particular matter. "
                    "Perhaps we might turn our attention to a question of mathematics? "
                    "There is always some beautiful identity waiting to be explored."
                )
            else:
                # Retry once
                try:
                    response = self._model.generate_content(
                        [
                            {"role": "user", "parts": [{"text": system_prompt}]},
                            {"role": "model", "parts": [{"text": "I understand. I am Srinivasa Ramanujan."}]},
                            {"role": "user", "parts": [{"text": user_input}]},
                        ]
                    )
                    response_text = response.text
                except Exception:
                    return (
                        "I must confess, something has interrupted my train of thought — "
                        "perhaps the postal service between here and Cambridge is unreliable "
                        "today. Would you be kind enough to ask me once more?"
                    )

        # ── Step 5: Update memories ───────────────────────────────────────
        self._short_term.add_turn("user", user_input)
        self._short_term.add_turn("ramanujan", response_text)

        # Detect topics for long-term memory
        self._update_long_term_memory(user_input, response_text)

        # ── Step 6: Return response ───────────────────────────────────────
        return response_text

    def _update_long_term_memory(self, user_input: str, response: str) -> None:
        """
        Analyze the exchange and update long-term memory with relevant topics
        and user characteristics.
        """
        combined = (user_input + " " + response).lower()

        # Track topics discussed
        topics_discussed = self._long_term.get("topics_discussed") or []
        for topic in SIGNATURE_TOPICS:
            if topic.lower() in combined and topic not in topics_discussed:
                topics_discussed.append(topic)

        if topics_discussed:
            self._long_term.update("topics_discussed", topics_discussed)

        # Track interaction count
        count = self._long_term.get("interaction_count") or 0
        self._long_term.update("interaction_count", count + 1)

        # Detect mathematical sophistication from user input
        advanced_keywords = [
            "modular", "analytic continuation", "asymptotic", "convergence",
            "zeta function", "riemann", "elliptic", "theta function",
            "generating function", "residue", "integral", "proof",
        ]
        user_lower = user_input.lower()
        if any(kw in user_lower for kw in advanced_keywords):
            self._long_term.update("user_math_level", "advanced")
        elif any(
            kw in user_lower
            for kw in ["derivative", "integral", "series", "formula", "equation"]
        ):
            current_level = self._long_term.get("user_math_level")
            if current_level != "advanced":
                self._long_term.update("user_math_level", "intermediate")

        # Detect moments of wonder in Ramanujan's response
        wonder_patterns = [
            "is it not extraordinary",
            "is it not remarkable",
            "how beautiful",
            "fills me with wonder",
        ]
        if any(pattern in response.lower() for pattern in wonder_patterns):
            wonder_count = self._long_term.get("moments_of_wonder") or 0
            self._long_term.update("moments_of_wonder", wonder_count + 1)

    def introspect(self) -> dict:
        """
        Return system status information.

        Returns:
            Dict with RAG stats, memory sizes, model name, and persona version.
        """
        rag_stats = self._rag.get_collection_stats()
        return {
            "scientist": SCIENTIST_NAME,
            "persona_version": PERSONA_VERSION,
            "knowledge_cutoff": KNOWLEDGE_CUTOFF_YEAR,
            "model": "gemini-2.5-flash",
            "rag_documents": rag_stats["total_documents"],
            "rag_collection": rag_stats["collection_name"],
            "short_term_turns": self._short_term.turn_count,
            "short_term_tokens": self._short_term.token_count(),
            "long_term_entries": self._long_term.entry_count,
        }

    def reset_session(self) -> None:
        """
        Clear short-term memory only.

        Long-term memory persists across sessions.
        """
        self._short_term.clear()

    @property
    def rag(self) -> RAGPipeline:
        """Access the RAG pipeline (for stats display in demo)."""
        return self._rag

    @property
    def long_term_memory(self) -> "LongTermMemory":
        """Access long-term memory (for display in demo)."""
        return self._long_term

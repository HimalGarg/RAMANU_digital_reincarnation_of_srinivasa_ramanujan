"""
agent/rag.py — RAG Pipeline
=============================
Retrieval-Augmented Generation pipeline using ChromaDB for vector storage
and sentence-transformers (all-MiniLM-L6-v2) for embeddings.
"""

import os
from typing import Optional

import chromadb
import tiktoken
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline.

    Manages document embedding, storage in ChromaDB, and retrieval of
    relevant context for the Ramanujan persona engine.
    """

    def __init__(
        self,
        persist_dir: str = "vectordb/",
        collection_name: str = "ramanujan_knowledge",
    ):
        """
        Initialize the RAG pipeline.

        Args:
            persist_dir: Directory for ChromaDB persistent storage.
            collection_name: Name of the ChromaDB collection.
        """
        self._persist_dir = os.path.abspath(persist_dir)
        self._collection_name = collection_name

        # Initialize ChromaDB persistent client
        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Load sentence-transformers model
        self._model: Optional[SentenceTransformer] = None

        # Tiktoken encoder for token counting
        self._tokenizer = tiktoken.get_encoding("cl100k_base")

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load the sentence-transformers model on first use."""
        if self._model is None:
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
        return self._model

    def embed_text(self, text: str) -> list[float]:
        """
        Compute embedding vector for a single string.

        Args:
            text: The text to embed.

        Returns:
            List of floats representing the embedding vector.
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def add_documents(self, docs: list[dict]) -> None:
        """
        Batch embed and upsert documents into ChromaDB.

        Args:
            docs: List of dicts, each with keys:
                  - "id" (str): Unique document identifier
                  - "text" (str): Document content
                  - "metadata" (dict): Associated metadata
        """
        if not docs:
            return

        # Process in batches for memory efficiency
        batch_size = 100
        for i in tqdm(range(0, len(docs), batch_size), desc="Embedding documents"):
            batch = docs[i : i + batch_size]

            ids = [doc["id"] for doc in batch]
            texts = [doc["text"] for doc in batch]
            metadatas = [doc.get("metadata", {}) for doc in batch]

            # Batch embed
            embeddings = self.model.encode(texts, convert_to_numpy=True).tolist()

            # Upsert into ChromaDB
            self._collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
            )

    def retrieve(self, query: str, n_results: int = 5) -> list[dict]:
        """
        Retrieve the most relevant documents for a query.

        Args:
            query: The search query string.
            n_results: Maximum number of results to return.

        Returns:
            List of dicts with keys: "id", "text", "metadata", "distance".
            Results with distance > 1.5 (too dissimilar) are filtered out.
        """
        # Check if collection has any documents
        if self._collection.count() == 0:
            return []

        query_embedding = self.embed_text(query)

        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, self._collection.count()),
            include=["documents", "metadatas", "distances"],
        )

        # Unpack and filter results
        retrieved = []
        if results and results["ids"] and results["ids"][0]:
            for idx in range(len(results["ids"][0])):
                distance = results["distances"][0][idx]

                # Filter out dissimilar results
                if distance > 1.5:
                    continue

                retrieved.append(
                    {
                        "id": results["ids"][0][idx],
                        "text": results["documents"][0][idx],
                        "metadata": results["metadatas"][0][idx] if results["metadatas"] else {},
                        "distance": distance,
                    }
                )

        return retrieved

    def format_context(self, results: list[dict]) -> str:
        """
        Format retrieved chunks into a clean context block for prompt injection.

        Includes source metadata labels and truncates to ~2000 tokens.

        Args:
            results: List of retrieval results from self.retrieve().

        Returns:
            Formatted context string with source labels.
        """
        if not results:
            return ""

        context_parts = []
        for result in results:
            metadata = result.get("metadata", {})
            source = metadata.get("source", "Unknown source")
            doc_type = metadata.get("type", "")

            # Build source label
            if doc_type == "letter":
                label = f"[From Ramanujan's letter — {source}]"
            elif doc_type == "notebook":
                label = f"[From Ramanujan's Notebook — {source}]"
            elif doc_type == "biography":
                label = f"[Biographical account — {source}]"
            else:
                label = f"[Source: {source}]"

            context_parts.append(f"{label}\n{result['text']}")

        full_context = "\n\n".join(context_parts)

        # Truncate to ~2000 tokens
        tokens = self._tokenizer.encode(full_context)
        if len(tokens) > 2000:
            truncated_tokens = tokens[:2000]
            full_context = self._tokenizer.decode(truncated_tokens) + "\n..."

        return full_context

    def get_collection_stats(self) -> dict:
        """
        Return statistics about the ChromaDB collection.

        Returns:
            Dict with "total_documents" and "collection_name".
        """
        return {
            "total_documents": self._collection.count(),
            "collection_name": self._collection_name,
        }

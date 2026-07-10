"""
RAG Tool — wraps VectorStore to provide a clean search interface
that returns results formatted for the agent / LLM.
"""

from __future__ import annotations

import logging

from app.services.vectorstore import VectorStore

logger = logging.getLogger(__name__)


class RAGTool:
    """Retrieval-augmented generation tool over policy documents."""

    def __init__(self, vector_store: VectorStore) -> None:
        self._vs = vector_store

    def search(self, query: str) -> dict:
        """Search the policy documents and return formatted results.

        Returns:
            {
                "results": [
                    {"content": "...", "source": "...", "section": "...", "score": 0.87},
                    ...
                ],
                "sources": ["hr_leave_policy.pdf", ...]
            }
        """
        hits = self._vs.search(query, top_k=5)

        # De-duplicate source list while preserving order
        seen: set[str] = set()
        sources: list[str] = []
        for h in hits:
            src = h["source"]
            if src not in seen:
                sources.append(src)
                seen.add(src)

        # Build a context string for the LLM
        formatted_results: list[dict] = []
        for i, hit in enumerate(hits, 1):
            formatted_results.append(
                {
                    "rank": i,
                    "content": hit["content"],
                    "source": hit["source"],
                    "section": hit["section"],
                    "score": hit["score"],
                }
            )

        logger.info("RAG search for '%s' returned %d results from %s", query, len(hits), sources)
        return {"results": formatted_results, "sources": sources}

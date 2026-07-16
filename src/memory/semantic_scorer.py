"""Semantic scoring boundaries for Discovery retrieval."""

from __future__ import annotations

import re
from typing import Protocol


class SemanticScorer(Protocol):
    """Deterministic scoring boundary for retrieval candidates.

    This protocol isolates semantic or lexical relevance calculation from
    structural relationship processing, allowing future embedding models to
    be plugged in seamlessly without exposing vector database details to the Planner.
    """

    def score(self, query: str, text: str) -> float:
        """Return a relevance score between 0.0 and 1.0."""
        ...


class LexicalScorer:
    """Deterministic keyword-based baseline for semantic similarity.

    Limitation: This system currently has no vector database or embedding
    infrastructure configured. This scorer provides a non-network, deterministic
    keyword intersection fallback to satisfy the Step 5 scorer requirement.
    It does not claim true vector-semantic capability.
    """

    def score(self, query: str | None, text: str | None) -> float:
        """Calculate simple Jaccard-like keyword overlap coefficient."""

        if not query or not text:
            return 0.0

        q_words = set(re.findall(r"\w+", query.lower()))
        t_words = set(re.findall(r"\w+", text.lower()))

        if not q_words or not t_words:
            return 0.0

        intersection = q_words.intersection(t_words)
        union = q_words.union(t_words)
        return len(intersection) / len(union)

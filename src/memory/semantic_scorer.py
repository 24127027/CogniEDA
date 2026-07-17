"""Deterministic relevance-scoring boundary for Discovery retrieval."""

from __future__ import annotations

import re
from typing import Protocol


class SemanticScorer(Protocol):
    """Return a deterministic relevance score from zero to one."""

    def score(self, query: str, text: str) -> float: ...


class LexicalScorer:
    """Small local keyword-overlap fallback; no vector retrieval is implied."""

    def score(self, query: str, text: str) -> float:
        query_words = set(re.findall(r"\w+", query.lower()))
        text_words = set(re.findall(r"\w+", text.lower()))
        if not query_words or not text_words:
            return 0.0
        return len(query_words & text_words) / len(query_words | text_words)

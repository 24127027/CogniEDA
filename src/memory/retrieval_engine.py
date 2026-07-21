"""Bounded, lifecycle-aware Discovery retrieval for planning prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlmodel import Session

from repositories.discovery_repository import DiscoveryRepository
from schemas.artifacts import Discovery, SessionFrame
from schemas.enums import ContextMode, FirstClassObjectType
from schemas.retrieval import RetrievalRequest, RetrievalResult, RetrievalResultItem

from .retrieval_policy import exclusion_reason
from .semantic_scorer import LexicalScorer, SemanticScorer


@dataclass
class _Candidate:
    discovery: Discovery
    score: float = 0.0
    inclusion_reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)


class DiscoveryRetrievalEngine:
    """Retrieve a small, explainable candidate set without mutating research state."""

    def __init__(self, session: Session, scorer: SemanticScorer | None = None) -> None:
        self._repository = DiscoveryRepository(session)
        self._scorer = scorer or LexicalScorer()

    def retrieve(
        self,
        request: RetrievalRequest,
        frame: SessionFrame | None = None,
    ) -> RetrievalResult:
        """Return lifecycle-filtered candidates ranked by frame affinity and query overlap."""

        result = RetrievalResult()
        frame_ids = set(frame.relevant_discovery_refs) if frame is not None else set()
        candidates_by_id: dict[UUID, _Candidate] = {}

        for discovery_id in frame_ids:
            discovery = self._repository.get_by_id(discovery_id)
            if discovery is not None:
                candidates_by_id[discovery_id] = _Candidate(discovery=discovery)
            else:
                result.exclusion_notes.append("A SessionFrame Discovery reference is unavailable.")

        for discovery in self._repository.list(limit=request.candidate_pool_limit):
            candidates_by_id.setdefault(discovery.discovery_id, _Candidate(discovery=discovery))

        ranked: list[_Candidate] = []
        for candidate in candidates_by_id.values():
            discovery = candidate.discovery
            reason = exclusion_reason(
                FirstClassObjectType.DISCOVERY,
                discovery.lifecycle_state,
                ContextMode.PLANNING,
            )
            if reason is not None:
                result.exclusion_notes.append(f"A Discovery candidate is excluded: {reason}")
                continue
            if discovery.discovery_id in frame_ids:
                candidate.score += 10.0
                candidate.inclusion_reasons.append("Included by the active SessionFrame.")
            query_text = request.query_text or ""
            lexical_score = self._scorer.score(
                query_text,
                f"{discovery.claim.statement} {discovery.scope}",
            )
            if lexical_score:
                candidate.score += lexical_score
                candidate.inclusion_reasons.append("Lexically relevant to the request.")
            if discovery.review_reasons:
                candidate.flags.append("Flagged for review: " + "; ".join(discovery.review_reasons))
            if candidate.score > 0.0:
                ranked.append(candidate)

        ranked.sort(
            key=lambda candidate: (
                -candidate.score,
                -candidate.discovery.created_at.timestamp(),
                str(candidate.discovery.discovery_id),
            )
        )
        for candidate in ranked[: request.max_results]:
            discovery = candidate.discovery
            result.candidates.append(
                RetrievalResultItem(
                    discovery_id=discovery.discovery_id,
                    claim_statement=discovery.claim.statement,
                    epistemic_status=discovery.epistemic_status,
                    lifecycle_state=discovery.lifecycle_state,
                    relevance_score=candidate.score,
                    inclusion_reasons=candidate.inclusion_reasons,
                    flags=candidate.flags,
                )
            )
        return result

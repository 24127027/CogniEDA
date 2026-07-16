"""Bounded Discovery retrieval for planner reasoning and decomposition."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlmodel import Session

from memory.retrieval_policy import exclusion_reason
from memory.semantic_scorer import LexicalScorer, SemanticScorer
from repositories.discovery_repository import DiscoveryRepository
from repositories.task_repository import TaskRepository
from schemas.artifacts import Discovery, SessionFrame, Task
from schemas.enums import ContextMode, DiscoveryLifecycleState, FirstClassObjectType
from schemas.retrieval import RetrievalRequest, RetrievalResult, RetrievalResultItem

logger = logging.getLogger(__name__)


@dataclass
class _CandidateContext:
    discovery: Discovery
    structural_score: float = 0.0
    semantic_score: float = 0.0
    structural_relations: list[str] = field(default_factory=list)
    inclusion_reasons: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    is_pinned: bool = False
    eligible_for_motivation: bool = True

    @property
    def total_score(self) -> float:
        return self.structural_score + self.semantic_score


class DiscoveryRetrievalEngine:
    """Bounded, lifecycle-aware Discovery retrieval engine."""

    def __init__(
        self,
        session: Session,
        scorer: SemanticScorer | None = None,
    ) -> None:
        self._session = session
        self._scorer = scorer or LexicalScorer()
        self._discovery_repo = DiscoveryRepository(session)
        self._task_repo = TaskRepository(session)

    def retrieve(
        self,
        request: RetrievalRequest,
        frame: SessionFrame | None = None,
    ) -> RetrievalResult:
        """Retrieve and rank discoveries for the requested planning context."""

        # 1. Resolve structural scope.
        ancestors, direct_parent = self._resolve_ancestors(request.parent_task_id)
        direct_motivation_ids = {
            d_id for d_id in (direct_parent.motivated_by_discovery_ids if direct_parent else [])
        }
        ancestor_motivation_ids = {
            d_id for task in ancestors for d_id in task.motivated_by_discovery_ids
        }

        result = RetrievalResult()
        pinned_ids = self._parse_discovery_ids(
            frame.user_pins if frame else [], label="pin", result=result
        )
        excluded_ids = self._parse_discovery_ids(
            frame.user_exclusions if frame else [], label="exclusion", result=result
        )
        active_data_profile_str = (
            str(request.active_data_profile_id) if request.active_data_profile_id else None
        )

        # 2. Generate a bounded candidate pool before scoring. Structural candidates
        # are always considered; the lexical fallback is a bounded recent window.
        structural_ids = {
            *direct_motivation_ids,
            *ancestor_motivation_ids,
            *pinned_ids,
            *(frame.relevant_discovery_refs if frame else []),
        }
        discoveries_by_id = {
            discovery.discovery_id: discovery
            for discovery_id in structural_ids
            if (discovery := self._discovery_repo.get_by_id(discovery_id)) is not None
        }
        for discovery in self._discovery_repo.list(limit=request.candidate_pool_limit):
            discoveries_by_id.setdefault(discovery.discovery_id, discovery)

        candidates: list[_CandidateContext] = []
        for discovery in discoveries_by_id.values():
            # Check explicit exclusion
            if discovery.discovery_id in excluded_ids:
                continue

            # 3. Apply lifecycle and validity policy
            reason = exclusion_reason(
                FirstClassObjectType.DISCOVERY,
                discovery.lifecycle_state,
                ContextMode.PLANNING,
            )

            is_pinned = discovery.discovery_id in pinned_ids

            if reason is not None:
                if discovery.lifecycle_state in {
                    DiscoveryLifecycleState.INVALIDATED,
                    DiscoveryLifecycleState.DEPRECATED,
                }:
                    if is_pinned:
                        result.exclusion_notes.append(
                            f"Pinned Discovery {discovery.discovery_id} is "
                            f"{discovery.lifecycle_state.value} and excluded."
                        )
                    continue
                if not is_pinned:
                    continue

            # 4. Calculate relevance features
            candidate = _CandidateContext(discovery=discovery, is_pinned=is_pinned)

            if is_pinned:
                candidate.structural_score += 100.0
                candidate.structural_relations.append("user_pinned")
                candidate.inclusion_reasons.append("Explicitly pinned by user.")

            if discovery.discovery_id in direct_motivation_ids:
                candidate.structural_score += 10.0
                candidate.structural_relations.append("direct_motivation")
                candidate.inclusion_reasons.append("Motivates the parent task.")

            if (
                discovery.discovery_id in ancestor_motivation_ids
                and discovery.discovery_id not in direct_motivation_ids
            ):
                candidate.structural_score += 5.0
                candidate.structural_relations.append("ancestor_motivation")
                candidate.inclusion_reasons.append("Motivates an ancestor task.")

            if active_data_profile_str:
                if discovery.validity_basis.data_profile_id == active_data_profile_str:
                    candidate.structural_score += 2.0
                    candidate.structural_relations.append("active_profile_match")
                elif discovery.validity_basis.data_profile_id:
                    candidate.structural_score -= 1.0
                    candidate.flags.append("Historically scoped to a different DataProfile.")
                    candidate.eligible_for_motivation = False
                else:
                    candidate.flags.append("No DataProfile scope is recorded for this Discovery.")
                    candidate.eligible_for_motivation = False

            # Flagged discoveries warnings
            if discovery.lifecycle_state == DiscoveryLifecycleState.FLAGGED:
                candidate.flags.append(f"Flagged for review: {'; '.join(discovery.review_reasons)}")
                candidate.eligible_for_motivation = False

            # Semantic/Lexical score
            candidate.semantic_score = self._scorer.score(
                request.query_text or "", f"{discovery.claim.statement} {discovery.scope}"
            )
            if candidate.semantic_score > 0.1 and not candidate.inclusion_reasons:
                candidate.inclusion_reasons.append("Semantically relevant to the request.")

            # Filter candidates that have no relevance and aren't pinned
            if candidate.total_score <= 0.0 and not is_pinned:
                continue

            candidates.append(candidate)

        # 5. Rank deterministically
        # Sort by total score DESC, then creation time DESC, then UUID ASC.
        candidates.sort(
            key=lambda c: (
                -c.total_score,
                -c.discovery.created_at.timestamp(),
                str(c.discovery.discovery_id),
            ),
        )

        # 6. Apply one strict, visible context budget. Pins receive structural
        # priority but exclusions and lifecycle validity always win.
        final_candidates = candidates[: request.max_results]

        # 7. Map to typed result separating motivation from context
        for c in final_candidates:
            item = RetrievalResultItem(
                discovery_id=c.discovery.discovery_id,
                claim_statement=c.discovery.claim.statement,
                epistemic_status=c.discovery.epistemic_status,
                lifecycle_state=c.discovery.lifecycle_state,
                relevance_score=c.total_score,
                structural_relations_used=c.structural_relations,
                inclusion_reasons=c.inclusion_reasons,
                flags=c.flags,
                is_pinned=c.is_pinned,
                eligible_for_motivation=c.eligible_for_motivation,
            )
            if c.eligible_for_motivation:
                result.motivation_candidates.append(item)
            else:
                result.other_relevant_discoveries.append(item)

        return result

    @staticmethod
    def _parse_discovery_ids(
        references: list[str],
        *,
        label: str,
        result: RetrievalResult,
    ) -> set[UUID]:
        ids: set[UUID] = set()
        for reference in references:
            try:
                ids.add(UUID(reference))
            except ValueError:
                result.exclusion_notes.append(
                    f"Ignoring non-Discovery SessionFrame {label}: {reference!r}."
                )
        return ids

    def _resolve_ancestors(self, parent_task_id: UUID | None) -> tuple[list[Task], Task | None]:
        if not parent_task_id:
            return [], None

        ancestors: list[Task] = []
        direct_parent = self._task_repo.get_by_id(parent_task_id)
        if direct_parent is None:
            return [], None

        current = direct_parent
        seen = {current.task_id}

        while current.parent_task_id:
            if current.parent_task_id in seen:
                break  # cycle
            seen.add(current.parent_task_id)
            next_parent = self._task_repo.get_by_id(current.parent_task_id)
            if next_parent is None:
                break
            ancestors.append(next_parent)
            current = next_parent

        return ancestors, direct_parent

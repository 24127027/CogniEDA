from __future__ import annotations

from uuid import uuid4

import pytest

from repositories import EvidenceRepository
from schemas.artifacts import Evidence
from schemas.common import EvidenceProvenance, EvidenceResultSummary
from schemas.enums import EvidenceType


def test_evidence_repository_rejects_orphan_before_foreign_key_flush(db_session) -> None:
    repository = EvidenceRepository(db_session)

    with pytest.raises(ValueError, match="existing Hypothesis"):
        repository.create(
            Evidence(
                hypothesis_id=uuid4(),
                profile_id=uuid4(),
                analysis_frame_ref="analysis-frame:missing",
                execution_run_ref="execution-run:missing",
                evidence_type=EvidenceType.STATISTICAL_TEST,
                method="chi_square",
                provenance=EvidenceProvenance(
                    analysis_frame_ref="analysis-frame:missing",
                    execution_run_ref="execution-run:missing",
                ),
                result_summary=EvidenceResultSummary(summary="Invalid orphan evidence."),
            )
        )

    assert repository.list() == []

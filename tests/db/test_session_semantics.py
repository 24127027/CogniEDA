from __future__ import annotations

from uuid import uuid4

import pytest

from cognieda.repositories import EvidenceRepository
from cognieda.schemas import Evidence, EvidenceProvenance


def test_evidence_repository_fails_closed_for_missing_mvp_lineage(db_session) -> None:
    data_profile_id = uuid4()
    evidence = Evidence(
        task_id=uuid4(),
        data_profile_id=data_profile_id,
        content={"row_count": 1},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference="de:missing",
            dataset_reference="dataset:missing.csv",
            data_profile_id=data_profile_id,
        ),
    )

    with pytest.raises(ValueError, match="existing Task"):
        EvidenceRepository(db_session).create(evidence)

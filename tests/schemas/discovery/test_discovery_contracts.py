"""Schema contracts and validation tests for discovery package."""

from __future__ import annotations

from uuid import UUID

import pytest
from pydantic import ValidationError

from schemas.common import DiscoveryClaim, ValidityBasis
from schemas.discovery import (
    Discovery,
)
from schemas.enums import (
    AnalysisIntent,
    DiscoveryEpistemicStatus,
)


def test_discovery_requires_evidence_and_matching_hypothesis() -> None:
    hyp_id = UUID("00000000-0000-0000-0000-000000000001")
    ev_id = UUID("00000000-0000-0000-0000-000000000002")

    claim = DiscoveryClaim(
        statement="Observed significant effect.",
        scope="dataset-v1",
        conditions=(),
        result="p_value < 0.05",
    )
    validity_basis = ValidityBasis(
        data_profile_id=UUID("00000000-0000-0000-0000-000000000003"),
        analysis_frame_refs=("frame-1",),
        hypothesis_id=hyp_id,
        evidence_ids=(ev_id,),
        method="t_test",
        decision_rule={},
        uncertainty="alpha=0.05",
        assumptions_excluded_from_inference=True,
    )

    discovery = Discovery(
        hypothesis_id=hyp_id,
        evidence_ids=[ev_id],
        claim=claim,
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="dataset-v1",
        validity_basis=validity_basis,
    )
    assert discovery.hypothesis_id == hyp_id
    assert discovery.analysis_intent == AnalysisIntent.EXPLORATORY

    # Mismatched hypothesis in validity_basis
    invalid_vb = ValidityBasis(
        data_profile_id=UUID("00000000-0000-0000-0000-000000000003"),
        analysis_frame_refs=("frame-1",),
        hypothesis_id=UUID("00000000-0000-0000-0000-000000000099"),
        evidence_ids=(ev_id,),
        method="t_test",
        decision_rule={},
        assumptions_excluded_from_inference=True,
    )
    with pytest.raises(ValidationError, match="same Hypothesis"):
        Discovery(
            hypothesis_id=hyp_id,
            evidence_ids=[ev_id],
            claim=claim,
            epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
            scope="dataset-v1",
            validity_basis=invalid_vb,
        )

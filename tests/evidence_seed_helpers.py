"""Test-only Evidence seeding below the sealed production writer boundary."""

from sqlmodel import Session

from repositories.evidence import EvidenceRepository
from schemas.evidence import Evidence


def seed_evidence_for_test(
    session: Session,
    evidence: Evidence,
    *,
    strict_provenance_validation: bool = False,
) -> Evidence:
    """Persist an Evidence fixture without reopening a production write path."""

    repository = EvidenceRepository(
        session,
        strict_provenance_validation=strict_provenance_validation,
    )
    repository._stage_create_from_evidence_admission(evidence)
    session.commit()
    persisted = repository.get_by_id(evidence.evidence_id)
    if persisted is None:
        raise AssertionError("Test Evidence seed was not persisted.")
    return persisted

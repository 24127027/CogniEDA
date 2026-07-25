"""Repository tests for ValidityEventRepository."""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlmodel import Session

from db.init_db import init_db
from db.models import GovernanceAuthorityRecord, ValidityEventRecord
from db.session import create_db_engine
from repositories.validity import ValidityEventRepository
from schemas.enums import AuthorizationClass, ValidityEventType, ValiditySourceType


@pytest.fixture
def session() -> Session:
    engine = create_db_engine("sqlite:///:memory:")
    init_db("sqlite:///:memory:")
    with Session(engine) as sess:
        yield sess


def test_validity_event_repository_staging_and_lookup(session: Session) -> None:
    repo = ValidityEventRepository(session)
    event_id = uuid4()
    src_id = uuid4()

    # Seed required FK GovernanceAuthorityRecord
    authority = GovernanceAuthorityRecord(
        authority_id=uuid4(),
        actor_identity="user-1",
        authority_class=AuthorizationClass.USER_GOVERNED,
        workspace_id="ws-1",
        session_id="sess-1",
        purpose="validity",
        operation_type="invalidate",
        issued_by="system",
        authority_fingerprint="fp-auth-val-1",
    )
    session.add(authority)
    session.flush()

    record = ValidityEventRecord(
        event_id=event_id,
        source_type=ValiditySourceType.EVIDENCE,
        source_id=src_id,
        event_type=ValidityEventType.EVIDENCE_INVALIDATION,
        reason="Test invalidation",
        authority_id=authority.authority_id,
        authority_identity="user-1",
        authority_class=AuthorizationClass.USER_GOVERNED,
        workspace_id="ws-1",
        expected_source_state="active",
        source_post_state="invalidated",
        idempotency_key="idem-key-100",
        event_fingerprint="fp-event-100",
        plan_fingerprint="fp-plan-100",
    )

    repo._stage_event_from_atomic_propagation(record)
    session.flush()

    by_key = repo.get_by_idempotency_key("idem-key-100")
    assert by_key is not None
    assert by_key.event_id == event_id

    by_id = repo.get_by_event_id(event_id)
    assert by_id is not None
    assert by_id.idempotency_key == "idem-key-100"

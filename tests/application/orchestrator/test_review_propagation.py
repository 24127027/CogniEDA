"""Guard the removed post-commit Discovery review propagation bypass."""

from uuid import uuid4

import pytest

from application.orchestrator.review_propagation import propagate_discovery_review


def test_review_propagation_requires_atomic_validity_service(db_session) -> None:
    with pytest.raises(RuntimeError, match="AtomicValidityPropagationService"):
        propagate_discovery_review(db_session, uuid4())

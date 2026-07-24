"""Propagation of Discovery review flags to exact motivated tasks."""

from uuid import UUID

from sqlmodel import Session


def propagate_discovery_review(session: Session, discovery_id: UUID) -> None:
    """Reject the removed post-commit Task review propagation path."""

    del session, discovery_id
    raise RuntimeError("Discovery-driven Task review is part of AtomicValidityPropagationService.")

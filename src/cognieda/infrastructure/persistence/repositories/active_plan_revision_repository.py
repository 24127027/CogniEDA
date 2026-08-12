"""Persistence for the sole active PlanRevision selection per Objective."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from cognieda.infrastructure.persistence.models import ActivePlanRevisionRecord
from cognieda.schemas.plan_revision import ActivePlanRevisionSelection


class ActivePlanRevisionRepository:
    """Stage and read explicit active revision workflow state."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, selection: ActivePlanRevisionSelection) -> None:
        """Stage the first active selection; replanning replacement is deferred."""

        if self.get_by_objective_id(selection.objective_id) is not None:
            raise ValueError("An active PlanRevision already exists for this Objective.")
        self._session.add(ActivePlanRevisionRecord(**selection.model_dump()))
        self._session.flush()

    def get_by_objective_id(
        self, objective_id: UUID
    ) -> ActivePlanRevisionSelection | None:
        record = self._session.get(ActivePlanRevisionRecord, objective_id)
        return (
            None
            if record is None
            else ActivePlanRevisionSelection.model_validate(record, from_attributes=True)
        )


__all__ = ("ActivePlanRevisionRepository",)

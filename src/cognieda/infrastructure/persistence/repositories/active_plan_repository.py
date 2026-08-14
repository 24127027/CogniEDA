"""Objective-scoped active selection for immutable Plans."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from cognieda.infrastructure.persistence.models import ActivePlanRecord, PlanRecord
from cognieda.infrastructure.persistence.repositories.plan_repository import PlanRepository
from cognieda.schemas.plan import Plan


class ActivePlanRepository:
    """Stage active-pointer transitions without mutating historical Plans."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def activate(self, plan: Plan) -> None:
        """Stage one active selection for the Plan's exact Objective."""

        header = self._session.get(PlanRecord, plan.plan_id)
        if header is None:
            raise ValueError("Active selection requires a persisted Plan.")
        if header.objective_id != plan.objective.objective_id:
            raise ValueError("Active Plan Objective identity is inconsistent.")

        selection = self._session.get(
            ActivePlanRecord,
            plan.objective.objective_id,
        )
        if selection is None:
            selection = ActivePlanRecord(
                objective_id=plan.objective.objective_id,
                plan_id=plan.plan_id,
            )
        else:
            selection.plan_id = plan.plan_id
        self._session.add(selection)

    def get_by_objective_id(self, objective_id: UUID) -> Plan | None:
        """Resolve the exact currently active Plan for one Objective."""

        selection = self._session.get(ActivePlanRecord, objective_id)
        if selection is None:
            return None
        plan = PlanRepository(self._session).get_by_id(selection.plan_id)
        if plan is None:
            raise ValueError("Active selection references a missing Plan.")
        if plan.objective.objective_id != objective_id:
            raise ValueError("Active selection crosses Objective identity.")
        return plan


__all__ = ("ActivePlanRepository",)

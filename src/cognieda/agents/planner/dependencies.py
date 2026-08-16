from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from cognieda.application.ports import ExecutorDispatcherPort
from cognieda.schemas.plan import Plan


@dataclass(frozen=True)
class PlannerToolDeps:
    """Model-hidden dependencies reserved for future semantic Planner tools."""

    dispatcher: ExecutorDispatcherPort


class PlanAdmissionPort(Protocol):
    """Deterministic Application-authority boundary for exact Plan admission."""

    def admit(self, plan: Plan) -> Plan: ...


__all__ = (
    "PlanAdmissionPort",
    "PlannerToolDeps",
)

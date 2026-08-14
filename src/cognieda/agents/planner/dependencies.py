from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from cognieda.application.ports import ExecutorDispatcherPort
from cognieda.schemas.artifacts import Evidence
from cognieda.schemas.plan import Plan

from .context import PlannerContext


class PlannerExecutionSessionPort(Protocol):
    """One model-hidden execution round over current authoritative state."""

    @property
    def context(self) -> PlannerContext: ...

    @property
    def progress_count(self) -> int: ...

    async def run_data_work(
        self,
        dispatcher: ExecutorDispatcherPort,
        *,
        task_id: UUID,
        requested_work: str,
    ) -> Evidence: ...


class PlannerExecutionSessionFactoryPort(Protocol):
    """Application-owned factory for one current-scope execution round."""

    def create(
        self,
        *,
        context: PlannerContext,
        active_plan: Plan,
    ) -> PlannerExecutionSessionPort: ...


@dataclass(frozen=True)
class PlannerDeps:
    """Model-hidden runtime authority and services available through RunContext."""

    dispatcher: ExecutorDispatcherPort
    execution_session_factory: PlannerExecutionSessionFactoryPort | None = None
    executor_tools_enabled: bool = False
    execution_session: PlannerExecutionSessionPort | None = None


__all__ = (
    "PlannerDeps",
    "PlannerExecutionSessionFactoryPort",
    "PlannerExecutionSessionPort",
)

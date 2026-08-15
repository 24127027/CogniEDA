from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from pydantic_ai.messages import ModelMessage

from cognieda.application.ports import ExecutorDispatcherPort
from cognieda.schemas.artifacts import Task
from cognieda.schemas.plan import Plan

from .context import PlannerContext
from .types import PlannerOutput


@dataclass(frozen=True)
class PlannerDeps:
    """Model-hidden dependencies reserved for future semantic Planner tools."""

    dispatcher: ExecutorDispatcherPort


class PlannerContextProviderPort(Protocol):
    """Outer-state adapter that materializes fresh Planner-readable authority."""

    def materialize(self) -> PlannerContext: ...


class PlanAdmissionPort(Protocol):
    """Deterministic Application-authority boundary for exact Plan admission."""

    def admit(self, plan: Plan, *, tasks: tuple[Task, ...]) -> Plan: ...


class PlannerCognitiveInvoker(Protocol):
    """One current-context PydanticAI invocation used by the Planner graph."""

    async def __call__(
        self,
        request: str,
        *,
        context: PlannerContext,
        candidate_plan: Plan | None = None,
        candidate_tasks: tuple[Task, ...] = (),
        message_history: list[ModelMessage] | None = None,
    ) -> PlannerOutput: ...


@dataclass(frozen=True)
class PlannerGraphContext:
    """Stable non-checkpointed services available to Planner graph nodes."""

    invoke_cognitive: PlannerCognitiveInvoker
    planner_context_provider: PlannerContextProviderPort
    plan_admission: PlanAdmissionPort


__all__ = (
    "PlanAdmissionPort",
    "PlannerCognitiveInvoker",
    "PlannerContextProviderPort",
    "PlannerDeps",
    "PlannerGraphContext",
)

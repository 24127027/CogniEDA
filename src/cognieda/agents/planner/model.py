from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic_ai.messages import ModelMessage

from cognieda.application.ports import AgentFactoryPort, ModelConfig

from .dependencies import PlannerDeps
from .types import (
    PlannerAnswerInput,
    PlannerDecision,
    PlannerModelInput,
    PlannerResponseDraft,
)

PlannerModelOutputT = TypeVar("PlannerModelOutputT")


@dataclass(frozen=True)
class PlannerModelResult[PlannerModelOutputT]:
    """Typed output plus the native messages produced by one model invocation."""

    output: PlannerModelOutputT
    new_messages: tuple[ModelMessage, ...]


class PlannerDecisionModel(Protocol):
    """Model boundary used by deterministic Planner orchestration."""

    async def decide(
        self,
        model_input: PlannerModelInput,
        *,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerDecision]: ...

    async def answer(
        self, answer_input: PlannerAnswerInput
    ) -> PlannerModelResult[PlannerResponseDraft]: ...


class PlannerModel:
    """PydanticAI adapter for typed Planner decisions and grounded answers."""

    def __init__(
        self,
        deps: PlannerDeps,
        agent_factory: AgentFactoryPort,
        model_config: ModelConfig,
    ) -> None:
        self.deps = deps
        self._agent = agent_factory.create_agent(
            worker="planner",
            config=model_config,
            deps_type=PlannerDeps,
            builtin_tools=(),
        )

    async def decide(
        self,
        model_input: PlannerModelInput,
        *,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerDecision]:
        prompt = (
            "Classify the latest request into exactly one bounded MVP Planner action.\n"
            "Use only the typed research-state projection below as authoritative state.\n"
            "Assumptions are planning context, never empirical support.\n"
            "For data work, propose one bounded Task instruction and select exactly one "
            "Capability enum. If no Objective exists, include objective_text only when the "
            "request states a sufficiently clear research Objective; otherwise return "
            "invalid_or_unsupported with a clarification message.\n"
            "Do not author a Hypothesis, protocol, method, decision rule, Evidence, Discovery, "
            "approval flow, Task DAG, or executor identifier.\n"
            f"Typed input:\n{model_input.model_dump_json()}"
        )
        result = await self._agent.run(
            prompt,
            output_type=PlannerDecision,
            deps=self.deps,
            message_history=list(message_history),
        )
        return PlannerModelResult(
            output=PlannerDecision.model_validate(result.output),
            new_messages=tuple(result.new_messages()),
        )

    async def answer(
        self, answer_input: PlannerAnswerInput
    ) -> PlannerModelResult[PlannerResponseDraft]:
        prompt = (
            "Answer the latest request using only the admitted Evidence in this typed input.\n"
            "Do not invent analysis, strengthen the Evidence, or treat omitted planning "
            "Assumptions as support. Mention material provenance or scope limits when useful.\n"
            f"Typed evidence input:\n{answer_input.model_dump_json()}"
        )
        result = await self._agent.run(
            prompt,
            output_type=PlannerResponseDraft,
            deps=self.deps,
        )
        return PlannerModelResult(
            output=PlannerResponseDraft.model_validate(result.output),
            new_messages=tuple(result.new_messages()),
        )

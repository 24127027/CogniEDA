from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic_ai.messages import ModelMessage

from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.agents.utilities import instruction

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
    def __init__(
        self,
        deps: PlannerDeps,
        agent_factory: AgentFactoryPort,
        model_config: ModelConfig,
    ):
        self.deps = deps
        self._agent_factory = agent_factory
        self._model_config = model_config

        self.answer_instruction = instruction.load("answer.txt")
        self.decide_instruction = instruction.load("decide.txt")

        self._reload_agent()

    def _reload_agent(self):
        self._agent = self._agent_factory.create_agent(
            worker="planner",
            config=self._model_config,
            deps_type=PlannerDeps,
            builtin_tools=(),
        )

    def reload_model(
        self,
        model_config: ModelConfig | None = None,
    ):
        if model_config is not None:
            self._model_config = model_config

        self._reload_agent()

    async def decide(
        self,
        model_input: PlannerModelInput,
        *,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerDecision]:
        prompt = (
            f"Typed input:\n{model_input.model_dump_json()}"
        )
        result = await self._agent.run(
            prompt,
            output_type=PlannerDecision,
            deps=self.deps,
            message_history=list(message_history),
            instructions=[self.decide_instruction]
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

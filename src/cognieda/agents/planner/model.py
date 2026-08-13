from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic_ai.messages import ModelMessage

from cognieda.agents.utilities import instruction
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
    output: PlannerModelOutputT
    new_messages: tuple[ModelMessage, ...]


class PlannerDecisionModel(Protocol):

    async def decide(
        self,
        model_input: PlannerModelInput,
        *,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerDecision]:
        ...

    async def answer(
        self,
        answer_input: PlannerAnswerInput,
    ) -> PlannerModelResult[PlannerResponseDraft]:
        ...

    def reload(
        self,
        *,
        model_config: ModelConfig | None = None,
        agent_instruction: str | None = None,
        recreate_agent: bool = False,
    ) -> None:
        ...


class PlannerModel:
    def __init__(
        self,
        *,
        deps: PlannerDeps,
        agent_factory: AgentFactoryPort,
        model_config: ModelConfig | None = None,
        agent_instruction: str = "",
    ):
        self.deps = deps
        self._agent_factory = agent_factory

        self._model_config = model_config
        self._agent_instruction = agent_instruction

        self._agent = None

        self._answer_instruction = ""
        self._decide_instruction = ""

        self._rebuild_instructions()

        if model_config is not None:
            self._create_agent()

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def _rebuild_instructions(self) -> None:
        self._decide_instruction = instruction.assemble(
            "decide.txt",
            agent_instruction=self._agent_instruction,
        )

        self._answer_instruction = instruction.assemble(
            "answer.txt",
            agent_instruction=self._agent_instruction,
        )

    def _create_agent(self) -> None:
        if self._model_config is None:
            raise RuntimeError(
                "Planner model configuration has not been configured."
            )

        self._agent = self._agent_factory.create_agent(
            worker="planner",
            config=self._model_config,
            deps_type=PlannerDeps,
            builtin_tools=(),
        )

    def _ensure_agent(self) -> None:
        if self._agent is None:
            self._create_agent()

    # ------------------------------------------------------------------ #
    # Runtime reconfiguration
    # ------------------------------------------------------------------ #

    def reload(
        self,
        *,
        model_config: ModelConfig | None = None,
        agent_instruction: str | None = None,
        recreate_agent: bool = False,
    ) -> None:

        if model_config is not None:
            self._model_config = model_config
            recreate_agent = True

        if agent_instruction is not None:
            self._agent_instruction = agent_instruction

        self._rebuild_instructions()

        if recreate_agent:
            self._agent = None

    # ------------------------------------------------------------------ #
    # Inference
    # ------------------------------------------------------------------ #

    async def decide(
        self,
        model_input: PlannerModelInput,
        *,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerDecision]:

        self._ensure_agent()

        result = await self._agent.run( #type: ignore
            f"Typed input:\n{model_input.model_dump_json()}",
            output_type=PlannerDecision,
            deps=self.deps,
            message_history=list(message_history),
            instructions=self._decide_instruction,
        )

        return PlannerModelResult(
            output=PlannerDecision.model_validate(result.output),
            new_messages=tuple(result.new_messages()),
        )

    async def answer(
        self,
        answer_input: PlannerAnswerInput,
    ) -> PlannerModelResult[PlannerResponseDraft]:

        self._ensure_agent()

        result = await self._agent.run( #type: ignore
            f"Typed evidence input:\n{answer_input.model_dump_json()}",
            output_type=PlannerResponseDraft,
            deps=self.deps,
            instructions=self._answer_instruction,
        )

        return PlannerModelResult(
            output=PlannerResponseDraft.model_validate(result.output),
            new_messages=tuple(result.new_messages()),
        )
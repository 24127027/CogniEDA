"""Pydantic AI model adapter for the Data Explorer workflow."""

from __future__ import annotations

from typing import Protocol

from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.agents.utilities import instruction

from .types import EvaluationOutput, PlanningOutput


# ---------------------------------------------------------------------------
# Protocol boundary
# ---------------------------------------------------------------------------


class DataExplorerDecisionModel(Protocol):
    """Typed model boundary used by the deterministic DE graph nodes."""

    async def plan(self, prompt: str) -> PlanningOutput: ...

    async def evaluate(self, prompt: str) -> EvaluationOutput: ...


# ---------------------------------------------------------------------------
# Concrete implementation
# ---------------------------------------------------------------------------


class DataExplorerModel:
    """Pydantic AI adapter that drives DE planning and evaluation via one agent."""

    def __init__(
        self,
        agent_factory: AgentFactoryPort,
        model_config: ModelConfig,
        agent_instruction: str | None = None,
    ) -> None:
        self._agent_factory = agent_factory
        self._model_config = model_config
        self._agent_instruction = agent_instruction

        self._planning_instruction = instruction.assemble(
            "planning.txt", agent_instruction
        )
        self._evaluate_instruction = instruction.assemble(
            "evaluate.txt", agent_instruction
        )

        self._reload_agent()

    def _reload_agent(self) -> None:
        self._agent = self._agent_factory.create_agent(
            worker="data_explorer",
            config=self._model_config,
            deps_type=type(None),
            builtin_tools=(),
        )

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
            self._planning_instruction = instruction.assemble(
                "planning.txt", agent_instruction
            )
            self._evaluate_instruction = instruction.assemble(
                "evaluate.txt", agent_instruction
            )

        if recreate_agent:
            self._reload_agent()

    async def plan(self, prompt: str) -> PlanningOutput:
        result = await self._agent.run(
            prompt,
            output_type=PlanningOutput,
            instructions=self._planning_instruction,
        )
        return PlanningOutput.model_validate(result.output)

    async def evaluate(self, prompt: str) -> EvaluationOutput:
        result = await self._agent.run(
            prompt,
            output_type=EvaluationOutput,
            instructions=self._evaluate_instruction,
        )
        return EvaluationOutput.model_validate(result.output)


__all__ = ("DataExplorerDecisionModel", "DataExplorerModel")

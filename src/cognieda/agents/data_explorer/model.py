"""Pydantic AI model adapter for the Data Explorer workflow.

The agent is created once at construction time without a bound DataFrame.
At each node invocation the caller supplies a live DataFrame via the
``toolsets`` parameter of ``agent.run()``, which injects the three
FunctionToolsets:
    - profiling_toolset(df) — schema inspection & profiling
    - eda_toolset(df)       — descriptive / exploratory analysis
    - sandbox_toolset(df)   — custom sandboxed Python/Pandas code

All three toolsets are visible to every node call; the per-call instruction
controls which tools each node is expected to invoke.
"""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.agents.utilities import instruction

from .dependencies import DEDependencies
from .tools import eda_toolset, profiling_toolset, sandbox_toolset
from .types import EvaluationOutput, PlanningOutput


# ---------------------------------------------------------------------------
# Protocol boundary
# ---------------------------------------------------------------------------


class DataExplorerDecisionModel(Protocol):
    """Typed model boundary used by the deterministic DE graph nodes."""

    async def plan(
        self,
        prompt: str,
        df: pd.DataFrame,
        *,
        deps: DEDependencies | None = None,
    ) -> PlanningOutput: ...

    async def evaluate(
        self,
        prompt: str,
        df: pd.DataFrame | None,
        *,
        deps: DEDependencies | None = None,
    ) -> EvaluationOutput: ...


# ---------------------------------------------------------------------------
# Concrete implementation
# ---------------------------------------------------------------------------


class DataExplorerModel:
    """Pydantic AI adapter that drives DE planning and evaluation.

    The underlying agent is constructed once.  At each call, live toolsets
    are built around a DataFrame copy and injected into the agent run so
    that the model can call them during its reasoning turn.
    """

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
        # Agent is built without tools; toolsets are injected per call.
        # deps_type is DEDependencies so that tools registered with @toolset.tool
        # can access RunContext[DEDependencies] and read the DataProfile / Objective.
        self._agent = self._agent_factory.create_agent(
            worker="data_explorer",
            config=self._model_config,
            deps_type=DEDependencies,
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

    def _build_toolsets(self, df: pd.DataFrame | None) -> list:
        """Build bound toolsets around the supplied DataFrame.

        When ``df`` is None (e.g. pure evaluation on already-collected results),
        an empty DataFrame is used so the toolset factories succeed but the
        model is not expected to call them.
        """
        frame = df if df is not None else pd.DataFrame()
        return [
            profiling_toolset(frame),
            eda_toolset(frame),
            sandbox_toolset(frame),
        ]

    async def plan(
        self,
        prompt: str,
        df: pd.DataFrame,
        *,
        deps: DEDependencies | None = None,
    ) -> PlanningOutput:
        """Invoke the planning agent with all toolsets and research context visible.

        The planning instruction tells the model to select tools for each step
        rather than calling them directly — the execute node does the actual
        dispatch.  Tools are still visible so the model can reason about what
        is available.  DEDependencies carries the DataProfile and Objective so
        that context-aware tools can validate column names at call time.
        """
        result = await self._agent.run(
            prompt,
            output_type=PlanningOutput,
            instructions=self._planning_instruction,
            toolsets=self._build_toolsets(df),
            deps=deps or DEDependencies(),
        )
        return PlanningOutput.model_validate(result.output)

    async def evaluate(
        self,
        prompt: str,
        df: pd.DataFrame | None = None,
        *,
        deps: DEDependencies | None = None,
    ) -> EvaluationOutput:
        """Invoke the evaluation agent with all toolsets and research context visible.

        Evaluation primarily inspects accumulated execution results from the
        state.  Tools are available in case the model needs to re-examine the
        data, but the evaluation instruction focuses the model on judging
        completeness rather than generating new analysis.
        """
        result = await self._agent.run(
            prompt,
            output_type=EvaluationOutput,
            instructions=self._evaluate_instruction,
            toolsets=self._build_toolsets(df),
            deps=deps or DEDependencies(),
        )
        return EvaluationOutput.model_validate(result.output)


__all__ = ("DataExplorerDecisionModel", "DataExplorerModel")

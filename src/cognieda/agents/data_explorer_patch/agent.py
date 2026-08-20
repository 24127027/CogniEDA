from __future__ import annotations

from dataclasses import replace

from cognieda.application.ports.llm import AgentFactoryPort, ModelConfig
from cognieda.delegation.capabilities import Capability
from cognieda.delegation.contracts import (
    ExecutionStatus,
    ExecutorRequest,
    ExecutorResult,
)

from .context import Context
from .dependencies import DataExplorerDeps
from .graph import build_graph
from .state import State
from .tools import eda, dataset_profiling, sandbox
class DataExplorer:
    CAPABILITIES: tuple[Capability, ...] = (
        Capability.DATA_ANALYSIS,
        Capability.DATA_PROFILING,
        Capability.DATA_TRANSFORMATION,
    )

    builtin_tools: tuple = (
        *eda.all(),
        *dataset_profiling.all(),
        *sandbox.all(),
    )

    def __init__(
        self,
        deps: DataExplorerDeps,
        *,
        config: ModelConfig | None = None,
        agent_factory: AgentFactoryPort,
    ) -> None:
        self._model_config = config
        self._agent_factory = agent_factory
        self.deps = deps
        self._agent = None

        self.graph = build_graph()

    async def run(self, request: ExecutorRequest) -> ExecutorResult:
        """ExecutorProvider contract entry point."""
        self._ensure_agent()

        input_state: State = {
            "input": request.input,
            "iterations": 0,
            "artifacts": [],
        }

        context = Context(
            agent=self._agent,
            deps=self.deps,
            context=request.context,
        )

        try:
            result = await self.graph.ainvoke(
                input_state,
                context=context,
            )
        except Exception as exc:
            return ExecutorResult(
                status=ExecutionStatus.FAILED,
                failure=str(exc),
                emitted_artifacts=(),
            )

        feedback = result.get("feedback", "")
        artifacts = tuple(result.get("artifacts", ()))

        if not feedback.upper().startswith("YES"):
            return ExecutorResult(
                status=ExecutionStatus.FAILED,
                failure=feedback or "DataExplorer did not complete the request.",
                emitted_artifacts=artifacts,
            )

        return ExecutorResult(
            status=ExecutionStatus.SUCCEEDED,
            failure=None,
            emitted_artifacts=artifacts,
        )

    async def reload(self) -> None:
        """Reload the underlying agent."""

        self._create_agent()

    def _ensure_agent(self) -> None:
        if self._agent is None:
            self._create_agent()

    def _create_agent(self) -> None:
        if self._model_config is None:
            raise RuntimeError(
                "Data Explorer model configuration has not been configured."
            )

        self._agent = self._agent_factory.create_agent(
            worker="data_explorer",
            config=self._model_config,
            deps_type=DataExplorerDeps,
            builtin_tools=self.builtin_tools,
        )
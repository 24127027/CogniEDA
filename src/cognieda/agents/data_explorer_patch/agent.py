"""Data Explorer agent — contract-native executor with LangGraph internal workflow.

Public API
----------
DataExplorer
    .run(request: ExecutorRequest) -> DataExplorerResult
        The ExecutorProvider contract entry point.
    .reload() -> None
        Reloads the agent factory and any other internal state.
Internal workflow (LangGraph graph)
------------------------------------
The graph: start -> planning -> execute -> check_result -> end
check_result can loop back to planning when execution output is incomplete.

The graph is used when no analysis_planner is injected. When analysis_planner
is supplied (typically in tests), DataExplorer.run() bypasses the graph and
calls the planner directly, producing a deterministic result.
"""
from cognieda.delegation.contracts import ExecutionStatus

from cognieda.application.ports.llm import AgentFactoryPort, ModelConfig
from cognieda.delegation.capabilities import Capability
from cognieda.delegation.contracts import ExecutorRequest, ExecutorResult

from .dependencies import DataExplorerDeps
from .state import State
from .context import Context
from .graph import build_graph

class DataExplorer:
    CAPABILITIES: tuple[Capability, ...] = (
    Capability.DATA_ANALYSIS,
    Capability.DATA_PROFILING,
    Capability.DATA_TRANSFORMATION,
    )

    builtin_tools: tuple[()] = ()

    def __init__(
        self,
        deps: DataExplorerDeps,
        *,
        config: ModelConfig,
        agent_factory: AgentFactoryPort,
    ) -> None:
        self._model_config = config
        self._agent_factory = agent_factory
        self.deps = deps

        self.graph = build_graph()

    async def run(self, request: ExecutorRequest) -> ExecutorResult:
        """ExecutorProvider contract entry point."""
        self._ensure_agent()

        input: State = {
            "input": request.input,
            "external_context": request.context.model_dump_json(),  # Serialize context to JSON string
        }
        context: Context = Context(agent=self._agent)

        try: 
            result = await self.graph.ainvoke(input, context=context)
        except Exception as e:
            return ExecutorResult(
                status=ExecutionStatus.FAILED,
                failure=str(e),
                emitted_artifacts=(),
            )

        return ExecutorResult(
            status=ExecutionStatus.SUCCEEDED,
            failure=None,
            emitted_artifacts=tuple(result.get("emitted_artifacts", ())),
        )

    async def reload(self) -> None:
        """Reloads the agent factory and any other internal state."""
        ...

    def _create_agent(self) -> None:
        if self._model_config is None:
            raise RuntimeError("Data Explorer model configuration has not been configured.")
        self._agent = self._agent_factory.create_agent(
            worker="data_explorer",
            config=self._model_config,
            deps_type=DataExplorerDeps,
            builtin_tools=self.builtin_tools,
        )

    def _ensure_agent(self):
        if self._agent is None:
            self._create_agent()
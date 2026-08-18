"""Data Explorer agent — contract-native executor with LangGraph internal workflow.

Public API
----------
DataExplorer
    .run(request: ExecutionRequest) -> DataExplorerResult
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


from cognieda.application.ports.llm import AgentFactoryPort, ModelConfig
from cognieda.delegation.capabilities import Capability
from cognieda.delegation.contracts import ExecutorInput, ExecutionResult

from .dependencies import DataExplorerDeps

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
        self.config = config
        self.agent_factory = agent_factory
        self.deps = deps

    async def run(self, request: ExecutorInput) -> ExecutionResult:
        """ExecutorProvider contract entry point."""
        ...

    async def reload(self) -> None:
        """Reloads the agent factory and any other internal state."""
        ...

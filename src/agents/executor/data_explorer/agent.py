"""Data Explorer capability provider."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic_ai import Agent

from agents.llm import ModelConfig, create_agent
from tools.builtin import AvailableBuiltinTools

from ..capabilities import Capability
from ..types import ExecutionFailure, ExecutionRequest, ExecutionStatus
from .graph import build_graph
from .state import State
from .types import DataExplorerResult


def create_de_agent(config: ModelConfig) -> Agent[None]:
    return create_agent(
        worker="data_explorer",
        config=config,
        deps_type=type(None),
        builtin_tools=(),
    )


@dataclass(slots=True)
class DataExplorerConfig:
    model: ModelConfig = field(default_factory=ModelConfig)


class DataExplorer:
    """Provider for bounded data analysis and profiling capability requests."""

    builtin_tools: tuple[AvailableBuiltinTools, ...] = ()

    def __init__(self, *, config: ModelConfig | None = None) -> None:
        self.config = config or ModelConfig()
        self.graph = build_graph(config=self.config)

    async def run(self, request: ExecutionRequest) -> DataExplorerResult:
        if request.capability == Capability.DATA_TRANSFORMATION:
            return DataExplorerResult(
                source_role="data_explorer",
                task_id=request.input.task.task_id,
                work_id=f"de:{request.input.task.task_id}",
                status=ExecutionStatus.BLOCKED,
                capability=request.capability,
                limitations=[
                    "Successor dataset and DataProfile creation are not implemented in S0."
                ],
                failure=ExecutionFailure(
                    code="successor_data_profile_not_implemented",
                    message=(
                        "DATA_TRANSFORMATION is blocked because it cannot yet create a "
                        "successor dataset state and DataProfile."
                    ),
                ),
            )
        if request.capability not in {
            Capability.DATA_ANALYSIS,
            Capability.DATA_PROFILING,
        }:
            raise ValueError(f"Data Explorer cannot provide {request.capability}.")

        initial_state: State = {
            "request": request,
            "raw_data_results": None,
            "observation": None,
            "data_profile_draft": None,
            "execution_logs": [],
            "retry_count": 0,
            "final_result": None,
        }
        result_state = await self.graph.ainvoke(initial_state)
        final_result = result_state.get("final_result")
        if not isinstance(final_result, DataExplorerResult):
            raise RuntimeError("Data Explorer graph did not return DataExplorerResult.")
        return final_result


DataExplorerExecutor = DataExplorer

__all__ = (
    "DataExplorer",
    "DataExplorerConfig",
    "DataExplorerExecutor",
    "DataExplorerResult",
    "create_de_agent",
)

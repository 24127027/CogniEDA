"""Data Explorer executor wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic_ai import Agent

from agents.llm import ModelConfig, create_agent
from tools.builtin_tools import AvailableBuiltinTools

from ..capabilities import Capability
from ..executor import Executor
from ..registry import executor_registry
from ..types import ExecutionRequest, ExecutionResult, ExecutorContext, ExecutorInput
from .graph import build_graph
from .state import State


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


@executor_registry.register(Capability.DATA_EXPLORATION)
class DataExplorer(Executor[State]):
	"""Executor that can produce Evidence or DataProfile drafts directly from raw data in RAM."""

	builtin_tools: tuple[AvailableBuiltinTools, ...] = ()

	def __init__(
		self,
		*,
		config: ModelConfig | None = None,
	) -> None:
		self.config = config or ModelConfig()

		super().__init__(
			lambda: build_graph(
				config=self.config,
			)
		)

	async def run(self, input: ExecutorInput, context: ExecutorContext) -> ExecutionResult:
		initial_state: State = {
			"request": self._build_request(input, context),
			"raw_data_results": None,
			"evidence_draft": None,
			"data_profile_draft": None,
			"execution_logs": [],
			"retry_count": 0,
			"final_result": None,
		}

		result_state = await self.graph.ainvoke(initial_state)
		final_result = result_state.get("final_result")
		if isinstance(final_result, ExecutionResult):
			return final_result

		return ExecutionResult.model_validate(result_state)

	def _build_request(self, input: ExecutorInput, context: ExecutorContext) -> ExecutionRequest:
		return ExecutionRequest(
			capability=Capability.DATA_EXPLORATION.id,
			input=input,
			context=context,
		)


DataExplorerExecutor = DataExplorer

__all__ = ("DataExplorer", "DataExplorerConfig", "DataExplorerExecutor", "create_de_agent")
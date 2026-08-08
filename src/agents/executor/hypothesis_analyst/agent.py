"""Hypothesis-analysis executor wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic_ai import Agent

from agents.llm import ModelConfig, create_agent
from schemas.artifacts import Discovery
from tools.builtin import AvailableBuiltinTools

from ..capabilities import Capability
from ..executor import Executor
from ..registry import executor_registry
from ..types import ExecutionRequest, ExecutionResult, ExecutorContext, ExecutorInput
from .graph import build_graph
from .deps import AdmissionCall, DispatcherCall
from .state import HAState, State


def _missing_dispatcher_call(request: ExecutionRequest) -> ExecutionResult:
    raise RuntimeError(
        "HypothesisAnalyst requires a dispatcher callable for Data Explorer delegation."
    )


def _missing_admission_call(draft: Discovery) -> bool:
    raise RuntimeError(
        "HypothesisAnalyst requires an admission callable for discovery validation."
    )


def create_ha_agent(config: ModelConfig) -> Agent[None]:
    return create_agent(
        worker="hypothesis_analyst",
        config=config,
        deps_type=type(None),
        builtin_tools=(),
    )


@dataclass(slots=True)
class HypothesisAnalystConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    mock_dispatcher_call: DispatcherCall = _missing_dispatcher_call
    mock_admission_call: AdmissionCall = _missing_admission_call


@executor_registry.register(Capability.HYPOTHESIS_TESTING)
class HypothesisAnalyst(Executor[State]):
    """Executor that can produce Evidence and Discovery drafts."""

    builtin_tools: tuple[AvailableBuiltinTools, ...] = ()

    def __init__(
        self,
        *,
        config: ModelConfig | None = None,
        mock_dispatcher_call: DispatcherCall | None = None,
        mock_admission_call: AdmissionCall | None = None,
    ) -> None:
        self.config = config or ModelConfig()
        self.mock_dispatcher_call = mock_dispatcher_call or _missing_dispatcher_call
        self.mock_admission_call = mock_admission_call or _missing_admission_call

        super().__init__(
            lambda: build_graph(
                config=self.config,
                mock_dispatcher_call=self.mock_dispatcher_call,
                mock_admission_call=self.mock_admission_call,
            )
        )

    async def run(self, input: ExecutorInput, context: ExecutorContext) -> ExecutionResult:
        initial_state: HAState = {
            "request": self._build_request(input, context),
            "hypothesis_draft": None,
            "de_capability_requests": [],
            "collected_evidence": [],
            "evaluation_outcome": None,
            "scientific_value": None,
            "discovery_draft": None,
            "execution_logs": [],
            "final_result": None,
        }

        result_state = await self.graph.ainvoke(initial_state)
        final_result = result_state.get("final_result")
        if isinstance(final_result, ExecutionResult):
            return final_result

        return ExecutionResult.model_validate(result_state)

    def _build_request(self, input: ExecutorInput, context: ExecutorContext) -> ExecutionRequest:
        return ExecutionRequest(
            capability=Capability.HYPOTHESIS_TESTING.id,
            input=input,
            context=context,
        )


HypothesisAnalystExecutor = HypothesisAnalyst

__all__ = (
    "AdmissionCall",
    "DispatcherCall",
    "HypothesisAnalyst",
    "HypothesisAnalystConfig",
    "HypothesisAnalystExecutor",
    "create_ha_agent",
)

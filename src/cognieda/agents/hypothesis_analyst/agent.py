"""Deferred Hypothesis Analyst donor wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic_ai import Agent

from cognieda.agents.data_explorer.contracts import DataExplorerResult
from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.delegation import Capability, ExecutionRequest
from cognieda.schemas.artifacts import Discovery

from .contracts import HypothesisAnalystResult
from .deps import AdmissionCall, DispatcherCall
from .graph import build_graph
from .state import HAState


def _missing_dispatcher_call(request: ExecutionRequest) -> DataExplorerResult:
    raise RuntimeError(
        "HypothesisAnalyst requires a dispatcher callable for Data Explorer delegation."
    )


def _missing_admission_call(draft: Discovery) -> bool:
    raise RuntimeError("HypothesisAnalyst requires an admission callable for discovery validation.")


def create_ha_agent(config: ModelConfig, agent_factory: AgentFactoryPort) -> Agent[None]:
    return agent_factory.create_agent(
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


class HypothesisAnalyst:
    """Import-safe donor scaffold; S0 does not register it as runnable."""

    builtin_tools: tuple[()] = ()

    def __init__(
        self,
        *,
        config: ModelConfig | None = None,
        agent_factory: AgentFactoryPort | None = None,
        mock_dispatcher_call: DispatcherCall | None = None,
        mock_admission_call: AdmissionCall | None = None,
    ) -> None:
        self.config = config or ModelConfig()
        self.agent_factory = agent_factory
        self.mock_dispatcher_call = mock_dispatcher_call or _missing_dispatcher_call
        self.mock_admission_call = mock_admission_call or _missing_admission_call
        self.graph = build_graph(
            config=self.config,
            agent_factory=agent_factory,
            mock_dispatcher_call=self.mock_dispatcher_call,
            mock_admission_call=self.mock_admission_call,
        )

    async def run(self, request: ExecutionRequest) -> HypothesisAnalystResult:
        if request.capability != Capability.HYPOTHESIS_TESTING:
            raise ValueError(f"Hypothesis Analyst cannot provide {request.capability}.")
        initial_state: HAState = {
            "request": request,
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
        if not isinstance(final_result, HypothesisAnalystResult):
            raise RuntimeError("Hypothesis Analyst graph did not return its role-native result.")
        return final_result


HypothesisAnalystExecutor = HypothesisAnalyst

__all__ = (
    "AdmissionCall",
    "DispatcherCall",
    "HypothesisAnalyst",
    "HypothesisAnalystConfig",
    "HypothesisAnalystExecutor",
    "HypothesisAnalystResult",
    "create_ha_agent",
)

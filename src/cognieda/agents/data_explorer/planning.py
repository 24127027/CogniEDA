"""Data Explorer-owned bounded operational planning."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_ai import Agent

from cognieda.application.ports import AgentFactoryPort, ModelConfig

from .contracts import DataAnalysisPlan, DataAnalysisPlanningRequest


class UnsupportedAnalysisRequest(ValueError):
    """The Task cannot be represented by the finite M3-A operation set."""


class DataAnalysisPlanningDecision(BaseModel):
    """Typed model decision: one valid plan or an explicit unsupported reason."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    plan: DataAnalysisPlan | None = None
    unsupported_reason: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _has_exactly_one_outcome(self) -> DataAnalysisPlanningDecision:
        if (self.plan is None) == (self.unsupported_reason is None):
            raise ValueError("Planning requires exactly one plan or unsupported reason.")
        return self


class ModelDataAnalysisPlanner:
    """Typed model adapter that proposes only a finite Data Explorer plan."""

    def __init__(self, *, config: ModelConfig, agent_factory: AgentFactoryPort) -> None:
        self._agent: Agent[None] = agent_factory.create_agent(
            worker="data_explorer",
            config=config,
            deps_type=type(None),
            builtin_tools=(),
        )

    async def propose(self, request: DataAnalysisPlanningRequest) -> DataAnalysisPlan:
        prompt = (
            "Translate this direct descriptive DATA Task into exactly one typed bounded "
            "DataAnalysisPlan. Choose only a supported operation and exact column names "
            "present in the supplied authoritative DataProfile. Do not calculate empirical "
            "results, write code, rename columns, infer synonyms, select scientific tests, "
            "or repair an unsupported request. Return either one valid plan or an explicit "
            "unsupported_reason; never return a fallback operation.\n"
            f"Typed planning input:\n{request.model_dump_json()}"
        )
        result = await self._agent.run(prompt, output_type=DataAnalysisPlanningDecision)
        decision = DataAnalysisPlanningDecision.model_validate(result.output)
        if decision.plan is None:
            assert decision.unsupported_reason is not None
            raise UnsupportedAnalysisRequest(decision.unsupported_reason)
        return decision.plan


__all__ = ("ModelDataAnalysisPlanner", "UnsupportedAnalysisRequest")

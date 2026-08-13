from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic_ai.messages import ModelMessage

from cognieda.application.planner_data_work import run_data_work
from cognieda.application.ports import AgentFactoryPort, ModelConfig

from .dependencies import PlannerDeps
from .types import (
    PlannerAnswerInput,
    PlannerDecision,
    PlannerModelInput,
    PlannerResponseDraft,
    PlannerTaskExecutionInput,
    PlannerTaskExecutionResponse,
)

PlannerModelOutputT = TypeVar("PlannerModelOutputT")


@dataclass(frozen=True)
class PlannerModelResult[PlannerModelOutputT]:
    """Typed output plus the native messages produced by one model invocation."""

    output: PlannerModelOutputT
    new_messages: tuple[ModelMessage, ...]


class PlannerDecisionModel(Protocol):
    """Model boundary used by deterministic Planner orchestration."""

    async def decide(
        self,
        model_input: PlannerModelInput,
        *,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerDecision]: ...

    async def answer(
        self, answer_input: PlannerAnswerInput
    ) -> PlannerModelResult[PlannerResponseDraft]: ...

    async def execute_task(
        self,
        execution_input: PlannerTaskExecutionInput,
        *,
        deps: PlannerDeps,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerTaskExecutionResponse]: ...


class PlannerModel:
    def __init__(
        self,
        deps: PlannerDeps,
        agent_factory: AgentFactoryPort,
        model_config: ModelConfig,
    ):
        self.deps = deps
        self._agent_factory = agent_factory
        self._model_config = model_config

        self._reload_agent()

    def _reload_agent(self) -> None:
        self._agent = self._agent_factory.create_agent(
            worker="planner",
            config=self._model_config,
            deps_type=PlannerDeps,
            builtin_tools=(run_data_work,),
        )

    def reload_model(
        self,
        model_config: ModelConfig | None = None,
    ) -> None:
        if model_config is not None:
            self._model_config = model_config

        self._reload_agent()

    async def decide(
        self,
        model_input: PlannerModelInput,
        *,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerDecision]:
        prompt = (
            "Reason about the latest Human request and return one bounded state-safe "
            "Planner decision.\n"
            "Use only the typed research-state projection below as authoritative state.\n"
            "Assumptions are Human-authored planning context, never empirical support. Never "
            "invent, infer, paraphrase, improve, or strengthen an Assumption. Only consider "
            "Assumption retention when the latest request explicitly supplies a statement as "
            "an assumption. Echo that statement as an exact contiguous verbatim substring of "
            "the latest request. Judge whether it is reasonably testable within the project, "
            "data, or research workflow. If it is not reasonably testable, return "
            "add_assumption with assumption_is_reasonably_testable=false. If it is reasonably "
            "testable, return invalid_or_unsupported with "
            "assumption_is_reasonably_testable=true; it must not become an Assumption because "
            "scientific investigation is not executable in this DATA-only runtime. A normal "
            "data or research request must never produce an Assumption.\n"
            "For data work, propose one semantic DATA Task instruction. Do not select a "
            "capability, provider, specialist, tool, or execution route. If no Objective "
            "exists, include objective_text only when the "
            "request states a sufficiently clear research Objective; otherwise return "
            "invalid_or_unsupported with a clarification message.\n"
            "You may answer directly, answer from authoritative retained state, clarify, "
            "establish or refine an Objective, propose semantic work, or report an unsupported "
            "request. Do not author a Hypothesis, protocol, method, decision rule, Evidence, "
            "Discovery, approval flow, or executor identifier.\n"
            f"Typed input:\n{model_input.model_dump_json()}"
        )
        result = await self._agent.run(
            prompt,
            output_type=PlannerDecision,
            deps=self.deps,
            message_history=list(message_history),
        )
        return PlannerModelResult(
            output=PlannerDecision.model_validate(result.output),
            new_messages=tuple(result.new_messages()),
        )

    async def answer(
        self, answer_input: PlannerAnswerInput
    ) -> PlannerModelResult[PlannerResponseDraft]:
        prompt = (
            "Answer the latest request using only the admitted Evidence in this typed input.\n"
            "Do not invent analysis, strengthen the Evidence, or treat omitted planning "
            "Assumptions as support. Mention material provenance or scope limits when useful.\n"
            f"Typed evidence input:\n{answer_input.model_dump_json()}"
        )
        result = await self._agent.run(
            prompt,
            output_type=PlannerResponseDraft,
            deps=self.deps,
        )
        return PlannerModelResult(
            output=PlannerResponseDraft.model_validate(result.output),
            new_messages=tuple(result.new_messages()),
        )

    async def execute_task(
        self,
        execution_input: PlannerTaskExecutionInput,
        *,
        deps: PlannerDeps,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlannerModelResult[PlannerTaskExecutionResponse]:
        prompt = (
            "Pursue the eligible approved Task as the current goal using only the governed "
            "tools available in this invocation. The application has already established "
            "eligibility and authoritative dataset binding. Use run_data_work to express "
            "semantic bounded data work; do not select a capability, provider, physical "
            "dataset path, or exact columns merely to bypass Data Explorer operationalization. "
            "You may call run_data_work zero, one, or multiple times as reasoning requires. "
            "Inspect each result, decide whether more work is needed, and stop when the Task "
            "goal is satisfied. If the available tool cannot satisfy the Task, return a clear "
            "blocker. A direct DATA result is not Evidence and must not be described as such.\n"
            f"Typed execution input:\n{execution_input.model_dump_json()}"
        )
        result = await self._agent.run(
            prompt,
            output_type=PlannerTaskExecutionResponse,
            deps=deps,
            message_history=list(message_history),
        )
        return PlannerModelResult(
            output=PlannerTaskExecutionResponse.model_validate(result.output),
            new_messages=tuple(result.new_messages()),
        )

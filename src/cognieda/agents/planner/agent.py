from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt
from pydantic_ai import Agent
from pydantic_ai.messages import ModelRequest, UserPromptPart

from cognieda.agents.utilities import instruction
from cognieda.application.ports import AgentFactoryPort, ModelConfig

from .context import PlannerContext
from .contracts import (
    PlannerControlledError,
    PlannerErrorCode,
    PlannerOutput,
    PlannerResult,
    PlanReviewAction,
    PlanReviewDecision,
)
from .dependencies import PlannerDeps
from .graph import build_graph
from .nodes import block_execution, execute_prompt, fail_state, plan_or_answer_prompt
from .state import PlannerState
from .tools import RUN_DATA_WORK_TOOL


class Planner:
    """Human-facing two-phase coordinator over typed research state."""

    builtin_tools = (RUN_DATA_WORK_TOOL,)

    def __init__(
        self,
        deps: PlannerDeps,
        *,
        agent_factory: AgentFactoryPort,
        model_config: ModelConfig | None,
        agent_instruction: str | None = None,
    ) -> None:
        self._deps = deps
        self._agent_factory = agent_factory
        self._model_config = model_config
        self._workspace_instruction = agent_instruction
        self._pending_threads: dict[UUID, str] = {}
        self._last_context: PlannerContext | None = None
        self._assemble_instructions()
        self._recreate_agent()
        self.graph = build_graph(self._plan_or_answer_node, self._execute_node)

    def _assemble_instructions(self) -> None:
        self._plan_or_answer_instructions = tuple(
            instruction.assemble(
                "plan_or_answer.txt",
                workspace_instruction=self._workspace_instruction,
            )
        )
        self._execute_instructions = tuple(
            instruction.assemble(
                "execute.txt",
                workspace_instruction=self._workspace_instruction,
            )
        )

    def _recreate_agent(self) -> None:
        self._agent: Agent[PlannerDeps, object] | None
        if self._model_config is None:
            self._agent = None
            return
        self._agent = self._agent_factory.create_agent(
            worker="planner",
            config=self._model_config,
            deps_type=PlannerDeps,
            builtin_tools=self.builtin_tools,
        )

    async def reload(
        self,
        *,
        model_config: ModelConfig | None = None,
        agent_instruction: str | None = None,
        recreate_agent: bool = False,
    ) -> None:
        """Reload phase instructions and optionally recreate the current Agent."""

        if model_config is not None:
            self._model_config = model_config
            recreate_agent = True
        if agent_instruction is not None:
            self._workspace_instruction = agent_instruction

        self._assemble_instructions()
        if recreate_agent:
            self._recreate_agent()

    async def run(
        self,
        request: str,
        *,
        context: PlannerContext,
    ) -> PlannerOutput:
        """Start one Planner lifecycle and pause when a candidate Plan needs review."""

        if not request.strip():
            error = PlannerControlledError(
                code=PlannerErrorCode.INVALID_COMMAND,
                message="Planner requests cannot be empty.",
            )
            return PlannerOutput(
                result=PlannerResult(response=error.message),
                error=error,
            )

        thread_id = str(uuid4())
        result = await self.graph.ainvoke(
            PlannerState(request=request, context=context),
            config=self._graph_config(thread_id),
        )
        state = self._state_from_result(result)
        self._last_context = state.context
        self._record_pending_thread(state, thread_id)
        return self._output_from_state(state)

    async def resume(
        self,
        decision: PlanReviewDecision,
        *,
        context: PlannerContext,
    ) -> PlannerOutput:
        """Resume the exact interrupted lifecycle after Application authority acts."""

        thread_id = self._pending_threads.pop(decision.plan_id, None)
        if thread_id is None:
            error = PlannerControlledError(
                code=PlannerErrorCode.INVALID_SUCCESSOR_STATE,
                message="No pending Planner lifecycle matches the reviewed Plan.",
            )
            return PlannerOutput(
                result=PlannerResult(response=error.message),
                error=error,
            )

        result = await self.graph.ainvoke(
            Command(
                update={"context": context},
                resume=decision.model_dump(mode="json"),
            ),
            config=self._graph_config(thread_id),
        )
        state = self._state_from_result(result)
        self._last_context = state.context
        self._record_pending_thread(state, thread_id)
        return self._output_from_state(state)

    async def _plan_or_answer_node(self, state: PlannerState) -> PlannerState:
        try:
            if self._agent is None:
                return fail_state(
                    state,
                    PlannerErrorCode.MODEL_UNAVAILABLE,
                    "Planner model configuration is unavailable.",
                )
            message_history = [
                *state.context.conversation_history.model_messages(),
                *state.messages,
            ]
            result = await self._agent.run(
                plan_or_answer_prompt(state),
                output_type=PlannerResult,
                message_history=message_history,
                instructions=self._plan_or_answer_instructions,
                deps=replace(
                    self._deps,
                    executor_tools_enabled=False,
                    execution_session=None,
                ),
            )
            planner_result = PlannerResult.model_validate(result.output)
            if planner_result.continue_execution:
                if state.context.active_plan is None:
                    raise ValueError(
                        "continue_execution requires an approved active Plan."
                    )
                if state.execution_blocker is not None:
                    raise ValueError(
                        "Execution cannot continue without resolving the prior blocker."
                    )
            if planner_result.plan is not None:
                admitted_assumptions = {
                    assumption.assumption_id: assumption
                    for assumption in state.context.assumptions
                }
                for assumption in planner_result.plan.assumptions:
                    if admitted_assumptions.get(assumption.assumption_id) != assumption:
                        raise ValueError(
                            "Candidate Plan Assumptions must exactly match admitted state."
                        )
            state.result = planner_result
            state.messages = (
                *state.messages,
                *result.all_messages()[len(message_history) :],
            )
            state.human_feedback = None
            state.error = None
        except Exception as exc:
            fail_state(
                state,
                PlannerErrorCode.INVALID_MODEL_RESULT,
                f"Planner could not produce a valid plan-phase result: {exc}",
            )
        return state

    async def _execute_node(self, state: PlannerState) -> PlannerState:
        planner_result = state.result
        if planner_result is None:
            return block_execution(
                state,
                PlannerErrorCode.INVALID_SUCCESSOR_STATE,
                "Execute requires an explicit Planner result.",
            )

        candidate = planner_result.plan
        if candidate is not None:
            review = PlanReviewDecision.model_validate(
                interrupt(
                    {
                        "plan_id": str(candidate.plan_id),
                        "plan": candidate.model_dump(mode="json"),
                        "tasks": [
                            task.model_dump(mode="json") for task in planner_result.tasks
                        ],
                    }
                )
            )
            if review.plan_id != candidate.plan_id:
                return block_execution(
                    state,
                    PlannerErrorCode.INVALID_SUCCESSOR_STATE,
                    "Human review identity does not match the interrupted Plan.",
                )
            state.messages = (*state.messages, self._human_review_message(review))
            if review.action is not PlanReviewAction.APPROVE:
                state.result = None
                state.human_feedback = review.feedback
                state.execution_blocker = None
                state.error = None
                return state
            if state.context.active_plan != candidate:
                return block_execution(
                    state,
                    PlannerErrorCode.INVALID_SUCCESSOR_STATE,
                    "Execute requires the exact approved Plan in current authoritative context.",
                )
        elif not planner_result.continue_execution:
            return block_execution(
                state,
                PlannerErrorCode.INVALID_SUCCESSOR_STATE,
                "Execute requires a candidate Plan or continue_execution.",
            )

        active_plan = state.context.active_plan
        if active_plan is None:
            return block_execution(
                state,
                PlannerErrorCode.INVALID_SUCCESSOR_STATE,
                "Execute requires an approved active Plan.",
            )
        state.result = None
        state.human_feedback = None
        try:
            if self._agent is None:
                return block_execution(
                    state,
                    PlannerErrorCode.MODEL_UNAVAILABLE,
                    "Planner model configuration is unavailable.",
                )
            if self._deps.execution_session_factory is None:
                state.execution_blocker = (
                    "Approved execution is unavailable because no Application execution "
                    "authority is configured."
                )
                state.error = None
                return state
            execution_session = self._deps.execution_session_factory.create(
                context=state.context,
                active_plan=active_plan,
            )
            message_history = [
                *state.context.conversation_history.model_messages(),
                *state.messages,
            ]
            result = await self._agent.run(
                execute_prompt(state, active_plan),
                output_type=str,
                message_history=message_history,
                instructions=self._execute_instructions,
                deps=replace(
                    self._deps,
                    executor_tools_enabled=True,
                    execution_session=execution_session,
                ),
            )
            state.messages = (
                *state.messages,
                *result.all_messages()[len(message_history) :],
            )
            state.context = execution_session.context
            state.execution_blocker = (
                None
                if execution_session.progress_count > 0
                else "Execute completed without an authoritative tool result or state change."
            )
            state.error = None
        except Exception as exc:
            block_execution(
                state,
                PlannerErrorCode.RESPONSE_FAILED,
                f"Planner could not produce a valid execute-phase result: {exc}",
            )
        return state

    @staticmethod
    def _graph_config(thread_id: str) -> RunnableConfig:
        return {"configurable": {"thread_id": thread_id}}

    @staticmethod
    def _state_from_result(result: object) -> PlannerState:
        if not isinstance(result, dict):
            raise TypeError("Planner graph returned a non-mapping state.")
        values = {name: result[name] for name in PlannerState.model_fields if name in result}
        return PlannerState.model_validate(values)

    def _record_pending_thread(self, state: PlannerState, thread_id: str) -> None:
        result = state.result
        if result is not None and result.plan is not None:
            self._pending_threads[result.plan.plan_id] = thread_id

    @staticmethod
    def _human_review_message(decision: PlanReviewDecision) -> ModelRequest:
        feedback = f" Feedback: {decision.feedback}" if decision.feedback else ""
        return ModelRequest(
            parts=[
                UserPromptPart(
                    content=(
                        f"Human Plan review: {decision.action.value.upper()} "
                        f"Plan {decision.plan_id}.{feedback}"
                    )
                )
            ]
        )

    @property
    def last_context(self) -> PlannerContext | None:
        """Return the successor readable context from the latest lifecycle snapshot."""

        return self._last_context

    @staticmethod
    def _output_from_state(state: PlannerState) -> PlannerOutput:
        if state.result is None:
            error = PlannerControlledError(
                code=PlannerErrorCode.RESPONSE_FAILED,
                message="Planner graph completed without a cognitive result.",
            )
            return PlannerOutput(
                result=PlannerResult(response=error.message),
                messages=state.messages,
                error=error,
            )
        return PlannerOutput(
            result=state.result,
            messages=state.messages,
            error=state.error,
        )


__all__ = ("Planner",)

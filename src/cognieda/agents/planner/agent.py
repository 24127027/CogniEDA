from __future__ import annotations

from dataclasses import replace
from uuid import UUID, uuid4

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, interrupt
from pydantic_ai import Agent

from cognieda.agents.utilities import instruction
from cognieda.application.ports import AgentFactoryPort, ModelConfig

from .context import PlannerContext
from .contracts import (
    PlannerCognitiveResult,
    PlannerControlledError,
    PlannerErrorCode,
    PlannerOutput,
    PlanReviewAction,
    PlanReviewDecision,
)
from .dependencies import PlannerDeps
from .graph import build_graph
from .nodes import execute_prompt, fail_state, plan_prompt
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
        self._assemble_instructions()
        self._recreate_agent()
        self.graph = build_graph(self._plan_node, self._execute_node)

    def _assemble_instructions(self) -> None:
        self._plan_instructions = tuple(
            instruction.assemble(
                "plan.txt",
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
                cognitive_result=PlannerCognitiveResult(response=error.message),
                error=error,
            )

        thread_id = str(uuid4())
        result = await self.graph.ainvoke(
            PlannerState(request=request, context=context),
            config=self._graph_config(thread_id),
        )
        state = self._state_from_result(result)
        self._record_pending_thread(state, thread_id)
        return self._output_from_state(state)

    async def resume(
        self,
        decision: PlanReviewDecision,
    ) -> PlannerOutput:
        """Resume the exact interrupted lifecycle after Application authority acts."""

        thread_id = self._pending_threads.pop(decision.plan_id, None)
        if thread_id is None:
            error = PlannerControlledError(
                code=PlannerErrorCode.INVALID_SUCCESSOR_STATE,
                message="No pending Planner lifecycle matches the reviewed Plan.",
            )
            return PlannerOutput(
                cognitive_result=PlannerCognitiveResult(response=error.message),
                error=error,
            )

        result = await self.graph.ainvoke(
            Command(resume=decision.model_dump(mode="json")),
            config=self._graph_config(thread_id),
        )
        state = self._state_from_result(result)
        self._record_pending_thread(state, thread_id)
        return self._output_from_state(state)

    async def _plan_node(self, state: PlannerState) -> PlannerState:
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
                plan_prompt(state),
                output_type=PlannerCognitiveResult,
                message_history=message_history,
                instructions=self._plan_instructions,
                deps=replace(
                    self._deps,
                    executor_tools_enabled=False,
                    approved_plan=None,
                    approved_tasks=(),
                    eligible_task_ids=frozenset(),
                    data_profile=None,
                ),
            )
            cognitive_result = PlannerCognitiveResult.model_validate(result.output)
            if cognitive_result.replan_reason is not None:
                raise ValueError("The plan phase cannot emit a replan request.")
            state.cognitive_result = cognitive_result
            state.messages = (
                *state.messages,
                *result.all_messages()[len(message_history) :],
            )
            state.approved_plan_id = None
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
        approved = state.cognitive_result
        if approved is None or approved.plan is None:
            return fail_state(
                state,
                PlannerErrorCode.INVALID_SUCCESSOR_STATE,
                "Execute requires one exact candidate Plan bundle.",
            )

        review = PlanReviewDecision.model_validate(
            interrupt(
                {
                    "plan_id": str(approved.plan.plan_id),
                    "plan": approved.plan.model_dump(mode="json"),
                    "tasks": [task.model_dump(mode="json") for task in approved.tasks],
                }
            )
        )
        if review.plan_id != approved.plan.plan_id:
            return fail_state(
                state,
                PlannerErrorCode.INVALID_SUCCESSOR_STATE,
                "Human review identity does not match the interrupted Plan.",
            )
        if review.action is not PlanReviewAction.APPROVE:
            state.cognitive_result = None
            state.approved_plan_id = None
            state.human_feedback = review.feedback
            state.error = None
            return state

        state.approved_plan_id = approved.plan.plan_id
        state.human_feedback = None
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
                execute_prompt(state, approved),
                output_type=PlannerCognitiveResult,
                message_history=message_history,
                instructions=self._execute_instructions,
                deps=replace(
                    self._deps,
                    executor_tools_enabled=True,
                    approved_plan=approved.plan,
                    approved_tasks=approved.tasks,
                    eligible_task_ids=frozenset(
                        approved.plan.eligible_task_ids(
                            completed_task_ids={
                                task.task_id
                                for task in approved.tasks
                                if task.status.value == "completed"
                            }
                        )
                    ),
                    execution_context=self._deps.execution_context.model_copy(
                        update={
                            "data_profile_id": (
                                state.context.data_profile.data_profile_id
                                if state.context.data_profile is not None
                                else None
                            )
                        }
                    ),
                    data_profile=state.context.data_profile,
                ),
            )
            cognitive_result = PlannerCognitiveResult.model_validate(result.output)
            if cognitive_result.plan is not None or cognitive_result.assumption_assessment:
                raise ValueError("The execute phase cannot author a Plan or Assumption assessment.")
            state.cognitive_result = cognitive_result
            state.messages = (
                *state.messages,
                *result.all_messages()[len(message_history) :],
            )
            state.error = None
            if cognitive_result.replan_reason is not None:
                state.approved_plan_id = None
                state.human_feedback = cognitive_result.replan_reason
        except Exception as exc:
            fail_state(
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
        result = state.cognitive_result
        if result is not None and result.plan is not None and state.approved_plan_id is None:
            self._pending_threads[result.plan.plan_id] = thread_id

    @staticmethod
    def _output_from_state(state: PlannerState) -> PlannerOutput:
        if state.cognitive_result is None:
            error = PlannerControlledError(
                code=PlannerErrorCode.RESPONSE_FAILED,
                message="Planner graph completed without a cognitive result.",
            )
            return PlannerOutput(
                cognitive_result=PlannerCognitiveResult(response=error.message),
                messages=state.messages,
                error=error,
            )
        return PlannerOutput(
            cognitive_result=state.cognitive_result,
            messages=state.messages,
            error=state.error,
        )


__all__ = ("Planner",)

from __future__ import annotations

from pydantic import ValidationError
from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage

from cognieda.agents.utilities import instruction
from cognieda.application.ports import AgentFactoryPort, ModelConfig

from .context import PlannerContext
from .dependencies import PlannerDeps
from .types import (
    PlannerControlledError,
    PlannerErrorCode,
    PlannerOutput,
    PlannerResult,
)


class Planner:
    """Human-facing cognitive coordinator over readable research state."""

    builtin_tools: tuple[()] = ()

    def __init__(
        self,
        deps: PlannerDeps,
        *,
        agent_factory: AgentFactoryPort,
        model_config: ModelConfig | None,
        agent_instruction: str | None = None,
    ) -> None:
        self.deps = deps
        self._agent_factory = agent_factory
        self._model_config = model_config
        self._agent_instruction = agent_instruction
        self._instructions = self._assemble_instructions()
        self._agent: Agent[PlannerDeps] | None = None
        if model_config is not None:
            self._create_agent()

    def _assemble_instructions(self) -> list[str]:
        return instruction.assemble(
            "plan_or_answer.txt",
            agent_instruction=self._agent_instruction,
        )

    def _create_agent(self) -> None:
        if self._model_config is None:
            raise RuntimeError("Planner model configuration has not been configured.")
        self._agent = self._agent_factory.create_agent(
            worker="planner",
            config=self._model_config,
            deps_type=PlannerDeps,
            builtin_tools=self.builtin_tools,
        )

    def _ensure_agent(self) -> Agent[PlannerDeps]:
        if self._agent is None:
            self._create_agent()
        agent = self._agent
        if agent is None:
            raise RuntimeError("Planner Agent creation did not return an Agent.")
        return agent

    async def reload(
        self,
        *,
        model_config: ModelConfig | None = None,
        agent_instruction: str | None = None,
        recreate_agent: bool = False,
    ) -> None:
        """Reload Planner configuration while preserving direct Agent ownership."""

        if model_config is not None:
            self._model_config = model_config
            recreate_agent = True
        if agent_instruction is not None:
            self._agent_instruction = agent_instruction
        self._instructions = self._assemble_instructions()
        if recreate_agent:
            self._agent = None

    async def run(
        self,
        request: str,
        *,
        context: PlannerContext,
        message_history: list[ModelMessage] | None = None,
    ) -> PlannerOutput:
        """Invoke plan_or_answer exactly once without mutation or execution."""

        if not request.strip():
            return self._controlled_output(
                PlannerErrorCode.INVALID_REQUEST,
                "Planner requests cannot be empty.",
            )

        try:
            agent = self._ensure_agent()
        except (RuntimeError, ValueError):
            return self._controlled_output(
                PlannerErrorCode.MODEL_UNAVAILABLE,
                "Planner model configuration is unavailable.",
            )

        prompt = self._build_prompt(request, context)
        messages: tuple[ModelMessage, ...] = ()
        try:
            run_result = await agent.run(
                prompt,
                output_type=PlannerResult,
                deps=self.deps,
                message_history=message_history,
                instructions=self._instructions,
            )
            messages = tuple(run_result.new_messages())
            result = PlannerResult.model_validate(run_result.output)
            self._validate_result_against_context(result, context)
        except (ValidationError, ValueError):
            return self._controlled_output(
                PlannerErrorCode.INVALID_MODEL_RESULT,
                "Planner produced a result that is invalid for the current context.",
                messages=messages,
            )
        except Exception:
            return self._controlled_output(
                PlannerErrorCode.MODEL_UNAVAILABLE,
                "Planner model invocation failed.",
                messages=messages,
            )

        return PlannerOutput(result=result, messages=messages)

    @staticmethod
    def _build_prompt(request: str, context: PlannerContext) -> str:
        readable_state = context.model_dump_json()
        return f"Human request:\n{request}\n\nTyped readable research state:\n{readable_state}"

    @staticmethod
    def _validate_result_against_context(
        result: PlannerResult,
        context: PlannerContext,
    ) -> None:
        if result.continue_execution and context.active_plan is None:
            raise ValueError("continue_execution requires an active Plan.")

        if result.plan is None:
            return

        admitted_assumptions = {
            assumption.assumption_id: assumption for assumption in context.assumptions
        }
        for assumption in result.plan.assumptions:
            admitted = admitted_assumptions.get(assumption.assumption_id)
            if admitted is None:
                raise ValueError("Candidate Plan references an unknown Assumption.")
            if admitted != assumption:
                raise ValueError("Candidate Plan changes the content of an admitted Assumption.")

    @staticmethod
    def _controlled_output(
        code: PlannerErrorCode,
        message: str,
        *,
        messages: tuple[ModelMessage, ...] = (),
    ) -> PlannerOutput:
        error = PlannerControlledError(code=code, message=message)
        return PlannerOutput(
            result=PlannerResult(response=message),
            messages=messages,
            error=error,
        )


__all__ = ("Planner",)

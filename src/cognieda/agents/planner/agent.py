from __future__ import annotations

from pydantic_ai import Agent

from cognieda.agents.utilities import instruction
from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.execution import ExecutorContext

from .context import Context, PlanningContext
from .dependencies import PlannerDeps
from .graph import build_graph
from .types import PlannerControlledError, PlannerErrorCode, PlannerOutput, State


class Planner:
    """Human-facing coordinator over typed MVP research state."""

    builtin_tools: tuple[()] = ()

    def __init__(
        self,
        deps: PlannerDeps,
        *,
        agent_factory: AgentFactoryPort,
        model_config: ModelConfig,
        agent_instruction: str | None = None,
    ) -> None:
        self.deps = deps
        self._agent_factory = agent_factory
        self._model_config = model_config
        self._workspace_instruction = agent_instruction
        self._assemble_instructions()
        self._recreate_agent()
        self.graph = build_graph()

    def _assemble_instructions(self) -> None:
        self._answer_instructions = tuple(
            instruction.assemble("answer.txt", self._workspace_instruction)
        )
        self._decide_instructions = tuple(
            instruction.assemble("decide.txt", self._workspace_instruction)
        )

    def _recreate_agent(self) -> None:
        self._agent: Agent[PlannerDeps, object] = self._agent_factory.create_agent(
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
        """Reload Planner instructions and optionally recreate its current Agent."""

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
        query: str,
        *,
        planning_context: PlanningContext,
        execution_context: ExecutorContext | None = None,
    ) -> PlannerOutput:
        """Run one request against explicit read-only context and return typed results."""

        if not query.strip():
            error = PlannerControlledError(
                code=PlannerErrorCode.INVALID_COMMAND,
                message="Planner requests cannot be empty.",
            )
            return PlannerOutput(response=error.message, error=error)

        state = State(
            query=query,
            execution_context=execution_context or ExecutorContext(),
        )
        context = Context(
            agent=self._agent,
            deps=self.deps,
            planning_context=planning_context,
            decide_instructions=self._decide_instructions,
            answer_instructions=self._answer_instructions,
        )
        result = await self.graph.ainvoke(state, context=context)
        final_state = State.model_validate(result)

        if final_state.response is None:
            error = PlannerControlledError(
                code=PlannerErrorCode.RESPONSE_FAILED,
                message="Planner graph completed without a human-facing response.",
            )
            final_state.error = error
            final_state.response = error.message

        return PlannerOutput(
            response=final_state.response,
            decision=final_state.decision,
            created_objective=final_state.created_objective,
            created_assumption=final_state.created_assumption,
            created_task=final_state.created_task,
            selected_capability=final_state.selected_capability,
            work_outcome=final_state.work_outcome,
            new_messages=final_state.new_messages,
            error=final_state.error,
        )

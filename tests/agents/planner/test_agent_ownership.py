from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.contracts import (
    PlannerCognitiveResult,
    PlanReviewAction,
    PlanReviewDecision,
)
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.tools import RUN_DATA_WORK_TOOL
from cognieda.application.ports import ModelConfig
from cognieda.execution import ExecutorDispatcher, ExecutorRegistry
from cognieda.schemas import Objective, Plan, PlanTaskBinding, Task, TaskKind


@dataclass
class FakeRunResult:
    output: object
    messages: tuple[ModelMessage, ...]

    def all_messages(self) -> list[ModelMessage]:
        return list(self.messages)


class RecordingAgent:
    def __init__(
        self,
        outputs: list[PlannerCognitiveResult],
        messages: list[tuple[ModelMessage, ...]] | None = None,
    ) -> None:
        self._outputs = iter(outputs)
        self._messages = iter(messages or [() for _ in outputs])
        self.calls: list[dict[str, object]] = []

    async def run(self, prompt: str, **kwargs: object) -> FakeRunResult:
        self.calls.append({"prompt": prompt, **kwargs})
        history = tuple(kwargs.get("message_history", ()))
        return FakeRunResult(next(self._outputs), (*history, *next(self._messages)))


class RecordingFactory:
    def __init__(self, agent: RecordingAgent) -> None:
        self.agent = agent
        self.calls: list[dict[str, object]] = []

    def create_agent(self, **kwargs: object) -> RecordingAgent:
        self.calls.append(kwargs)
        return self.agent

    def reload_tooling(self) -> None:
        pass


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


def _candidate(label: str = "original") -> PlannerCognitiveResult:
    objective = Objective(text=f"Investigate {label} retention.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction=f"Profile {label} retention data.",
    )
    plan = Plan.create(
        objective=objective,
        task_bindings=(PlanTaskBinding(task_id=task.task_id, order_rank=0),),
        tasks=(task,),
    )
    return PlannerCognitiveResult(plan=plan, tasks=(task,), response="Review the Plan.")


def _planner(agent: RecordingAgent) -> Planner:
    return Planner(
        PlannerDeps(ExecutorDispatcher(ExecutorRegistry())),
        agent_factory=RecordingFactory(agent),  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="test", api_key="key"),
    )


def test_planner_owns_one_agent_and_exact_dependency_instance() -> None:
    agent = RecordingAgent([PlannerCognitiveResult(response="Done.")])
    factory = RecordingFactory(agent)
    deps = PlannerDeps(ExecutorDispatcher(ExecutorRegistry()))
    config = ModelConfig(provider="openai", model_name="test", api_key="key")

    planner = Planner(deps, agent_factory=factory, model_config=config)  # type: ignore[arg-type]

    assert planner._agent is agent
    assert planner._deps is deps
    assert factory.calls == [
        {
            "worker": "planner",
            "config": config,
            "deps_type": PlannerDeps,
            "builtin_tools": (RUN_DATA_WORK_TOOL,),
        }
    ]
    assert inspect.signature(Planner).parameters["deps"].default is inspect.Parameter.empty


def test_langgraph_has_exactly_two_cognitive_node_names() -> None:
    planner = _planner(RecordingAgent([PlannerCognitiveResult(response="Done.")]))
    graph = planner.graph.get_graph()

    assert set(graph.nodes) == {"__start__", "plan", "execute", "__end__"}
    assert "human_check" not in graph.nodes
    assert "run_planner" not in graph.nodes
    assert "compose_authoritative_answer" not in graph.nodes


def test_plan_interrupt_then_approval_resumes_execute_and_accumulates_messages() -> None:
    candidate = _candidate()
    plan_messages = _messages("plan", "candidate")
    execute_messages = _messages("execute", "complete")
    agent = RecordingAgent(
        [candidate, PlannerCognitiveResult(response="Execution complete.")],
        [plan_messages, execute_messages],
    )
    planner = _planner(agent)

    pending = asyncio.run(planner.run("Investigate retention", context=PlannerContext()))
    completed = asyncio.run(
        planner.resume(
            PlanReviewDecision(
                action=PlanReviewAction.APPROVE,
                plan_id=candidate.plan.plan_id,  # type: ignore[union-attr]
            )
        )
    )

    assert pending.cognitive_result == candidate
    assert pending.messages == plan_messages
    assert completed.cognitive_result.response == "Execution complete."
    assert completed.messages == (*plan_messages, *execute_messages)
    assert len(agent.calls) == 2
    assert agent.calls[0]["output_type"] is PlannerCognitiveResult
    assert agent.calls[1]["output_type"] is PlannerCognitiveResult
    plan_deps = agent.calls[0]["deps"]
    execute_deps = agent.calls[1]["deps"]
    assert isinstance(plan_deps, PlannerDeps) and not plan_deps.executor_tools_enabled
    assert plan_deps.approved_plan is None
    assert isinstance(execute_deps, PlannerDeps) and execute_deps.executor_tools_enabled
    assert execute_deps.approved_plan == candidate.plan


def test_rejection_feedback_routes_to_new_plan_and_requires_another_interrupt() -> None:
    original = _candidate("original")
    replacement = _candidate("revised")
    agent = RecordingAgent([original, replacement])
    planner = _planner(agent)

    asyncio.run(planner.run("Investigate retention", context=PlannerContext()))
    pending_replacement = asyncio.run(
        planner.resume(
            PlanReviewDecision(
                action=PlanReviewAction.REVISE,
                plan_id=original.plan.plan_id,  # type: ignore[union-attr]
                feedback="Narrow the population to active customers.",
            )
        )
    )

    assert pending_replacement.cognitive_result == replacement
    assert "Narrow the population" in str(agent.calls[1]["prompt"])
    assert replacement.plan is not None
    assert replacement.plan.plan_id in planner._pending_threads


def test_instruction_reload_preserves_agent_unless_recreation_requested() -> None:
    first = RecordingAgent([PlannerCognitiveResult(response="first")])
    second = RecordingAgent([PlannerCognitiveResult(response="second")])

    class Factory(RecordingFactory):
        def __init__(self) -> None:
            self.calls: list[dict[str, object]] = []
            self._agents = iter((first, second))

        def create_agent(self, **kwargs: object) -> RecordingAgent:
            self.calls.append(kwargs)
            return next(self._agents)

    factory = Factory()
    planner = Planner(
        PlannerDeps(ExecutorDispatcher(ExecutorRegistry())),
        agent_factory=factory,  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="test", api_key="key"),
    )

    asyncio.run(planner.reload(agent_instruction="workspace guidance"))
    assert planner._agent is first
    assert planner._plan_instructions[1] == "workspace guidance"
    assert planner._execute_instructions[1] == "workspace guidance"

    asyncio.run(planner.reload(recreate_agent=True))
    assert planner._agent is second

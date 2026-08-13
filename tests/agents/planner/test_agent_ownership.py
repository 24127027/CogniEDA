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
from cognieda.agents.planner.context import PlannerGraphContext
from cognieda.agents.planner.contracts import (
    AuthoritativeAnswerRequest,
    DirectResponse,
    PlannerCognitiveResult,
)
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.graph import build_graph
from cognieda.application.ports import ModelConfig
from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.planner_context import build_planner_context
from cognieda.schemas.artifacts import DataProfile, Evidence, Objective, SessionFrame, Task
from cognieda.schemas.common import EvidenceProvenance
from cognieda.schemas.enums import TaskKind, TaskStatus


@dataclass
class FakeRunResult:
    output: object
    messages: tuple[ModelMessage, ...]

    def new_messages(self) -> list[ModelMessage]:
        return list(self.messages)


class RecordingAgent:
    def __init__(
        self,
        result: PlannerCognitiveResult,
        answer: DirectResponse | None = None,
        result_messages: tuple[ModelMessage, ...] = (),
        answer_messages: tuple[ModelMessage, ...] = (),
    ) -> None:
        self._result = result
        self._answer = answer or DirectResponse(text="unused")
        self._result_messages = result_messages
        self._answer_messages = answer_messages
        self.calls: list[dict[str, object]] = []

    async def run(self, prompt: str, **kwargs: object) -> FakeRunResult:
        self.calls.append({"prompt": prompt, **kwargs})
        if kwargs["output_type"] == PlannerCognitiveResult:
            return FakeRunResult(self._result, self._result_messages)
        if kwargs["output_type"] is DirectResponse:
            return FakeRunResult(self._answer, self._answer_messages)
        raise AssertionError(f"Unexpected output type: {kwargs['output_type']}")


class RecordingFactory:
    def __init__(self, *agents: RecordingAgent) -> None:
        self._agents = iter(agents)
        self.calls: list[dict[str, object]] = []

    def create_agent(self, **kwargs: object) -> RecordingAgent:
        self.calls.append(kwargs)
        return next(self._agents)

    def reload_tooling(self) -> None:
        pass


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


def _agent(label: str = "unused") -> RecordingAgent:
    return RecordingAgent(DirectResponse(text=label))


def _evidence_frame() -> SessionFrame:
    objective = Objective(text="Understand dataset size.")
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Count rows.",
        status=TaskStatus.COMPLETED,
    )
    profile = DataProfile(row_count=42, column_count=0, columns=())
    evidence = Evidence(
        task_id=task.task_id,
        data_profile_id=profile.data_profile_id,
        content={"row_count": 42},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference="work:count-rows",
            dataset_reference="dataset:v1",
            data_profile_id=profile.data_profile_id,
        ),
    )
    return SessionFrame(
        objective=objective,
        tasks=(task,),
        data_profile=profile,
        evidences=(evidence,),
    )


def test_planner_constructs_and_owns_agent_and_dependency() -> None:
    config = ModelConfig(provider="openai", model_name="test", api_key="test-key")
    agent = _agent()
    factory = RecordingFactory(agent)
    deps = PlannerDeps()

    planner = Planner(deps, agent_factory=factory, model_config=config)

    assert planner._agent is agent
    assert planner._deps is deps
    assert factory.calls == [
        {
            "worker": "planner",
            "config": config,
            "deps_type": PlannerDeps,
            "builtin_tools": (),
        }
    ]
    assert inspect.signature(Planner).parameters["deps"].default is inspect.Parameter.empty
    assert PlannerDeps.__dataclass_fields__ == {}


def test_graph_context_names_each_runtime_category() -> None:
    assert set(PlannerGraphContext.model_fields) == {
        "agent",
        "deps",
        "planner_context",
        "conversation_history",
        "planner_instructions",
        "answer_instructions",
    }


def test_langgraph_contains_only_cognitive_and_protected_answer_stages() -> None:
    graph = build_graph().get_graph()

    assert set(graph.nodes) == {
        "__start__",
        "run_planner",
        "compose_authoritative_answer",
        "__end__",
    }
    edges = {(edge.source, edge.target, edge.conditional) for edge in graph.edges}
    assert ("__start__", "run_planner", False) in edges
    assert ("run_planner", "compose_authoritative_answer", True) in edges
    assert ("run_planner", "__end__", True) in edges
    assert ("compose_authoritative_answer", "__end__", False) in edges


def test_both_agent_runs_use_same_agent_and_exact_dependency_instance() -> None:
    prior_messages = _messages("Earlier request", "Earlier response")
    cognitive_messages = _messages("Current request", "Protected answer requested")
    answer_messages = _messages("Answer context", "Grounded response")
    agent = RecordingAgent(
        AuthoritativeAnswerRequest(),
        DirectResponse(text="The admitted Evidence reports 42 rows."),
        cognitive_messages,
        answer_messages,
    )
    deps = PlannerDeps()
    planner = Planner(
        deps,
        agent_factory=RecordingFactory(agent),  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="test", api_key="key"),
    )
    history = ConversationHistory().add_turn(prior_messages)

    output = asyncio.run(
        planner.run(
            "How many rows are present?",
            planner_context=build_planner_context(_evidence_frame()),
            conversation_history=history,
        )
    )

    assert output.response == "The admitted Evidence reports 42 rows."
    assert output.new_messages == (*cognitive_messages, *answer_messages)
    assert [call["output_type"] for call in agent.calls] == [
        PlannerCognitiveResult,
        DirectResponse,
    ]
    assert agent.calls[0]["message_history"] == list(prior_messages)
    assert "message_history" not in agent.calls[1]
    assert all(call["deps"] is deps for call in agent.calls)


def test_instruction_reload_updates_layers_without_recreating_agent() -> None:
    agent = _agent()
    factory = RecordingFactory(agent)
    planner = Planner(
        PlannerDeps(),
        agent_factory=factory,  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="initial", api_key="key"),
    )

    asyncio.run(planner.reload(agent_instruction="workspace-specific guidance"))

    assert planner._agent is agent
    assert len(factory.calls) == 1
    assert planner._planner_instructions[1] == "workspace-specific guidance"
    assert planner._answer_instructions[1] == "workspace-specific guidance"
    assert "Reason about the current Human request" in planner._planner_instructions[-1]


def test_recreation_uses_current_model_configuration_and_same_deps_type() -> None:
    first, second, third = _agent("first"), _agent("second"), _agent("third")
    factory = RecordingFactory(first, second, third)
    initial = ModelConfig(provider="openai", model_name="initial", api_key="key")
    updated = ModelConfig(provider="google", model_name="updated", api_key="key")
    planner = Planner(
        PlannerDeps(),
        agent_factory=factory,  # type: ignore[arg-type]
        model_config=initial,
    )

    asyncio.run(planner.reload(recreate_agent=True))
    assert planner._agent is second
    asyncio.run(planner.reload(model_config=updated))
    assert planner._agent is third
    assert factory.calls[-1]["config"] == updated
    assert all(call["deps_type"] is PlannerDeps for call in factory.calls)

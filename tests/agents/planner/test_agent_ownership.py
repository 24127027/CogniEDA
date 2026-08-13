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
from cognieda.agents.planner.contracts import (
    AnswerFromContextDecision,
    PlannerDecision,
    PlannerResponseDraft,
    StateSummaryDecision,
)
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
        decision: PlannerDecision,
        response: PlannerResponseDraft,
        decision_messages: tuple[ModelMessage, ...] = (),
        response_messages: tuple[ModelMessage, ...] = (),
    ) -> None:
        self._decision = decision
        self._response = response
        self._decision_messages = decision_messages
        self._response_messages = response_messages
        self.calls: list[dict[str, object]] = []

    async def run(self, prompt: str, **kwargs: object) -> FakeRunResult:
        self.calls.append({"prompt": prompt, **kwargs})
        if kwargs["output_type"] is PlannerDecision:
            return FakeRunResult(self._decision, self._decision_messages)
        if kwargs["output_type"] is PlannerResponseDraft:
            return FakeRunResult(self._response, self._response_messages)
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
    return RecordingAgent(StateSummaryDecision(), PlannerResponseDraft(text=label))


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


def test_planner_constructs_and_owns_agent_from_factory() -> None:
    config = ModelConfig(provider="openai", model_name="test", api_key="test-key")
    agent = _agent()
    factory = RecordingFactory(agent)

    planner = Planner(
        agent_factory=factory,  # type: ignore[arg-type]
        model_config=config,
    )

    assert planner._agent is agent
    assert factory.calls == [
        {
            "worker": "planner",
            "config": config,
            "deps_type": type(None),
            "builtin_tools": (),
        }
    ]
    assert "planner_model" not in inspect.signature(Planner).parameters
    assert "deps" not in inspect.signature(Planner).parameters


def test_langgraph_has_only_current_routing_free_lifecycle_nodes() -> None:
    graph = build_graph().get_graph()

    assert set(graph.nodes) == {
        "__start__",
        "understand_request",
        "prepare_results",
        "compose_response",
        "__end__",
    }
    assert {(edge.source, edge.target) for edge in graph.edges} == {
        ("__start__", "understand_request"),
        ("understand_request", "prepare_results"),
        ("prepare_results", "compose_response"),
        ("compose_response", "__end__"),
    }


def test_graph_nodes_use_same_agent_and_keep_new_messages_as_delta() -> None:
    prior_messages = _messages("Earlier request", "Earlier response")
    decision_messages = _messages("Current request", "Typed decision")
    response_messages = _messages("Answer context", "Grounded response")
    agent = RecordingAgent(
        AnswerFromContextDecision(),
        PlannerResponseDraft(text="The admitted Evidence reports 42 rows."),
        decision_messages,
        response_messages,
    )
    planner = Planner(
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
    assert output.new_messages == (*decision_messages, *response_messages)
    assert [call["output_type"] for call in agent.calls] == [
        PlannerDecision,
        PlannerResponseDraft,
    ]
    assert agent.calls[0]["message_history"] == list(prior_messages)
    assert "message_history" not in agent.calls[1]
    assert "deps" not in agent.calls[0]
    assert "deps" not in agent.calls[1]


def test_instruction_reload_updates_layers_without_recreating_agent() -> None:
    agent = _agent()
    factory = RecordingFactory(agent)
    planner = Planner(
        agent_factory=factory,  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="initial", api_key="key"),
    )

    asyncio.run(planner.reload(agent_instruction="workspace-specific guidance"))

    assert planner._agent is agent
    assert len(factory.calls) == 1
    assert planner._decide_instructions[1] == "workspace-specific guidance"
    assert planner._answer_instructions[1] == "workspace-specific guidance"
    assert "Classify the current request" in planner._decide_instructions[-1]
    assert "Answer the current request" in planner._answer_instructions[-1]


def test_recreation_uses_current_model_configuration() -> None:
    first, second, third = _agent("first"), _agent("second"), _agent("third")
    factory = RecordingFactory(first, second, third)
    initial = ModelConfig(provider="openai", model_name="initial", api_key="key")
    updated = ModelConfig(provider="google", model_name="updated", api_key="key")
    planner = Planner(
        agent_factory=factory,  # type: ignore[arg-type]
        model_config=initial,
    )

    asyncio.run(planner.reload(recreate_agent=True))
    assert planner._agent is second
    asyncio.run(planner.reload(model_config=updated))
    assert planner._agent is third
    assert factory.calls[-1]["config"] == updated

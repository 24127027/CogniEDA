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
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.types import (
    PlannerAction,
    PlannerDecision,
    PlannerResponseDraft,
)
from cognieda.application.ports import ModelConfig
from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.planner_context import build_planning_context
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
        decision_messages: tuple[ModelMessage, ...],
        response_messages: tuple[ModelMessage, ...],
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
    def __init__(self, agent: RecordingAgent) -> None:
        self.agent = agent
        self.calls: list[dict[str, object]] = []

    def create_agent(self, **kwargs: object) -> RecordingAgent:
        self.calls.append(kwargs)
        return self.agent

    def reload_tooling(self) -> None:
        pass


class NeverDispatcher:
    async def dispatch(self, request: object) -> None:
        raise AssertionError(f"Unexpected dispatch: {request}")


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


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
    agent = RecordingAgent(
        PlannerDecision(action=PlannerAction.STATE_SUMMARY),
        PlannerResponseDraft(text="unused"),
        (),
        (),
    )
    factory = RecordingFactory(agent)
    deps = PlannerDeps(dispatcher=NeverDispatcher())  # type: ignore[arg-type]

    planner = Planner(
        deps=deps,
        agent_factory=factory,  # type: ignore[arg-type]
        model_config=config,
    )

    assert planner._agent is agent
    assert factory.calls == [
        {
            "worker": "planner",
            "config": config,
            "deps_type": PlannerDeps,
            "builtin_tools": (),
        }
    ]
    assert "planner_model" not in inspect.signature(Planner).parameters


def test_graph_nodes_invoke_same_planner_agent_and_preserve_native_messages() -> None:
    prior_messages = _messages("Earlier request", "Earlier response")
    decision_messages = _messages("Current request", "Typed decision")
    response_messages = _messages("Evidence input", "Grounded response")
    agent = RecordingAgent(
        PlannerDecision(action=PlannerAction.ANSWER_FROM_STATE),
        PlannerResponseDraft(text="The admitted Evidence reports 42 rows."),
        decision_messages,
        response_messages,
    )
    planner = Planner(
        deps=PlannerDeps(dispatcher=NeverDispatcher()),  # type: ignore[arg-type]
        agent_factory=RecordingFactory(agent),  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="test", api_key="test-key"),
    )
    history = ConversationHistory().add_turn(prior_messages)
    context = build_planning_context(_evidence_frame(), history)

    output = asyncio.run(
        planner.run("How many rows are present?", planning_context=context)
    )

    assert output.response == "The admitted Evidence reports 42 rows."
    assert output.new_messages == (*decision_messages, *response_messages)
    assert [call["output_type"] for call in agent.calls] == [
        PlannerDecision,
        PlannerResponseDraft,
    ]
    assert agent.calls[0]["message_history"] == list(prior_messages)
    assert agent.calls[0]["deps"] is planner.deps
    assert agent.calls[1]["deps"] is planner.deps
    assert agent.calls[0]["instructions"] == planner._decide_instructions
    assert agent.calls[1]["instructions"] == planner._answer_instructions

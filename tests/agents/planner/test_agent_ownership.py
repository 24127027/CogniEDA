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


class SequenceFactory:
    def __init__(self, *agents: RecordingAgent) -> None:
        self._agents = iter(agents)
        self.calls: list[dict[str, object]] = []

    def create_agent(self, **kwargs: object) -> RecordingAgent:
        self.calls.append(kwargs)
        return next(self._agents)

    def reload_tooling(self) -> None:
        pass


class ToolingAwareFactory:
    def __init__(self, initial: RecordingAgent, reloaded: RecordingAgent) -> None:
        self._current = initial
        self._reloaded = reloaded

    def create_agent(self, **_: object) -> RecordingAgent:
        return self._current

    def reload_tooling(self) -> None:
        self._current = self._reloaded


class NeverDispatcher:
    async def dispatch(self, request: object) -> None:
        raise AssertionError(f"Unexpected dispatch: {request}")


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


def _recording_agent(label: str) -> RecordingAgent:
    return RecordingAgent(
        PlannerDecision(action=PlannerAction.STATE_SUMMARY),
        PlannerResponseDraft(text=label),
        (),
        (),
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


def test_instruction_reload_updates_layers_without_recreating_agent() -> None:
    agent = _recording_agent("current")
    factory = RecordingFactory(agent)
    planner = Planner(
        deps=PlannerDeps(dispatcher=NeverDispatcher()),  # type: ignore[arg-type]
        agent_factory=factory,  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="initial", api_key="key"),
    )

    asyncio.run(planner.reload(agent_instruction="workspace-specific guidance"))

    assert planner._agent is agent
    assert len(factory.calls) == 1
    assert planner._workspace_instruction == "workspace-specific guidance"
    assert planner._decide_instructions[1] == "workspace-specific guidance"
    assert planner._answer_instructions[1] == "workspace-specific guidance"
    assert "Classify the latest request" in planner._decide_instructions[-1]
    assert "Answer the latest request" in planner._answer_instructions[-1]


def test_explicit_recreation_and_model_change_replace_agent_with_current_config() -> None:
    first = _recording_agent("first")
    second = _recording_agent("second")
    third = _recording_agent("third")
    factory = SequenceFactory(first, second, third)
    initial_config = ModelConfig(
        provider="openai", model_name="initial", api_key="initial-key"
    )
    updated_config = ModelConfig(
        provider="google", model_name="updated", api_key="updated-key"
    )
    planner = Planner(
        deps=PlannerDeps(dispatcher=NeverDispatcher()),  # type: ignore[arg-type]
        agent_factory=factory,  # type: ignore[arg-type]
        model_config=initial_config,
    )

    asyncio.run(planner.reload(recreate_agent=True))
    assert planner._agent is second
    assert factory.calls[-1]["config"] == initial_config

    asyncio.run(planner.reload(model_config=updated_config))
    assert planner._agent is third
    assert factory.calls[-1]["config"] == updated_config


def test_recreation_uses_agent_factory_current_tooling_state() -> None:
    initial = _recording_agent("initial tooling")
    reloaded = _recording_agent("reloaded tooling")
    factory = ToolingAwareFactory(initial, reloaded)
    planner = Planner(
        deps=PlannerDeps(dispatcher=NeverDispatcher()),  # type: ignore[arg-type]
        agent_factory=factory,  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="test", api_key="key"),
    )

    factory.reload_tooling()
    asyncio.run(planner.reload(recreate_agent=True))

    assert planner._agent is reloaded

from typing import Any, cast

import pytest
from langgraph.runtime import Runtime
from pydantic_ai.messages import ModelRequest, UserPromptPart

from agents.planner.graph import INTENT_ROUTES, build_graph
from agents.planner.nodes import (
    _ConfiguredRequestUnderstandingModel,
    contextual_grounding,
    registry,
    route_intent,
    understand_request,
)
from agents.planner.types import (
    COMMAND_TO_INTENT,
    Context,
    RequestUnderstanding,
    RequestUnderstandingModel,
    State,
    parse_explicit_command,
)


class FakeRequestUnderstandingModel(RequestUnderstandingModel):
    def __init__(self, result: object) -> None:
        self.result = result
        self.prompts: list[str] = []

    def understand(self, prompt: str) -> RequestUnderstanding:
        self.prompts.append(prompt)
        return cast(RequestUnderstanding, self.result)


class FakeTaskManagementModel:
    def __init__(self, result: Any = None) -> None:
        self.result = result
        self.prompts: list[str] = []

    def draft(self, prompt: str) -> Any:
        self.prompts.append(prompt)
        from agents.planner.nodes import TaskManagementDraft
        return self.result or TaskManagementDraft()


def runtime_with(model: RequestUnderstandingModel | None = None) -> Runtime[Context]:
    return Runtime(context=Context(
        request_understanding_model=model,
        task_management_model=FakeTaskManagementModel(),
    ))


@pytest.mark.parametrize(
    ("query", "intent", "request_text"),
    [
        ("/answer What was discovered?", "answer", "What was discovered?"),
        (
            "/manage_task create a profiling task",
            "manage_task",
            "create a profiling task",
        ),
        ("   /objective refine the objective", "objective", "refine the objective"),
        ("/ANSWER What was discovered?", "answer", "What was discovered?"),
        ("/answer", "answer", ""),
    ],
)
def test_explicit_commands_bypass_the_model(
    query: str,
    intent: str,
    request_text: str,
) -> None:
    model = FakeRequestUnderstandingModel(
        RequestUnderstanding(intent="suggest", request_text="unexpected", source="llm")
    )

    result = understand_request(State(query=query), runtime_with(model))

    assert result.request_understanding == RequestUnderstanding(
        intent=intent,
        request_text=request_text,
        source="explicit_command",
        explicit_command=intent,
    )
    assert model.prompts == []


def test_parse_explicit_command_preserves_payload_and_normalizes_command() -> None:
    result = parse_explicit_command("  /MANAGE_TASK  retain   inner whitespace  ")

    assert result is not None
    assert result.command == "manage_task"
    assert result.original_command == "/MANAGE_TASK"
    assert result.request_text == "retain   inner whitespace"


def test_slash_later_in_text_uses_the_model_once() -> None:
    model = FakeRequestUnderstandingModel(
        RequestUnderstanding(
            intent="answer",
            request_text="Explain the difference between / and division.",
            source="llm",
        )
    )

    result = understand_request(
        State(query="Explain the difference between / and division."),
        runtime_with(model),
    )

    assert result.request_understanding is not None
    assert result.request_understanding.intent == "answer"
    assert len(model.prompts) == 1


def test_unknown_command_requires_correction_without_model_fallback() -> None:
    model = FakeRequestUnderstandingModel(
        RequestUnderstanding(intent="answer", request_text="unexpected", source="llm")
    )

    result = understand_request(State(query="/unknown remove everything"), runtime_with(model))

    understanding = result.request_understanding
    assert understanding is not None
    assert understanding.intent is None
    assert understanding.source == "invalid_command"
    assert understanding.requires_user_correction is True
    assert understanding.explicit_command == "/unknown"
    assert understanding.supported_commands == tuple(f"/{key}" for key in COMMAND_TO_INTENT)
    assert model.prompts == []
    assert route_intent(result, runtime_with(model)) == "invalid_request"


@pytest.mark.parametrize(
    ("intent", "expected_route_key"),
    [
        ("answer", "check_answerability"),
        ("suggest", "suggest"),
        ("manage_task", "manage_task"),
        ("execute", "execute"),
        ("objective", "objective"),
        ("assumption", "assumption"),
    ],
)
def test_route_intent_is_deterministic(
    intent: str,
    expected_route_key: str,
) -> None:
    model = FakeRequestUnderstandingModel(
        RequestUnderstanding(intent="answer", request_text="unexpected", source="llm")
    )
    state = State(
        query="ignored",
        request_understanding=RequestUnderstanding(
            intent=intent,
            request_text="normalized",
            source="llm",
        ),
    )

    assert route_intent(state, runtime_with(model)) == expected_route_key
    assert model.prompts == []


def test_natural_language_request_calls_model_once_with_only_latest_request() -> None:
    query = "Create a new task to inspect missing values."
    model = FakeRequestUnderstandingModel(
        RequestUnderstanding(
            intent="manage_task",
            request_text="inspect missing values",
            source="llm",
        )
    )

    result = understand_request(
        State(
            query=query,
            history=[ModelRequest(parts=[UserPromptPart(content="history-only-secret")])],
        ),
        runtime_with(model),
    )

    assert result.request_understanding is not None
    assert result.request_understanding.intent == "manage_task"
    assert len(model.prompts) == 1
    assert query in model.prompts[0]
    assert "history-only-secret" not in model.prompts[0]


def test_invalid_structured_model_result_uses_controlled_invalid_route() -> None:
    model = FakeRequestUnderstandingModel({"request_text": "missing intent"})

    result = understand_request(State(query="What has been discovered?"), runtime_with(model))

    understanding = result.request_understanding
    assert understanding is not None
    assert understanding.intent is None
    assert understanding.source == "invalid_llm"
    assert understanding.requires_user_correction is True
    assert route_intent(result, runtime_with(model)) == "invalid_request"
    assert len(model.prompts) == 1


def test_model_exception_uses_controlled_invalid_route() -> None:
    class RaisingRequestUnderstandingModel(RequestUnderstandingModel):
        def understand(self, prompt: str) -> RequestUnderstanding:
            raise RuntimeError("model unavailable")

    result = understand_request(
        State(query="What has been discovered?"),
        runtime_with(RaisingRequestUnderstandingModel()),
    )

    assert result.request_understanding is not None
    assert result.request_understanding.source == "invalid_llm"
    assert route_intent(result, runtime_with()) == "invalid_request"


def test_configured_request_adapter_uses_factory_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    from types import SimpleNamespace

    factory_call: dict[str, object] = {}

    class FakeAgent:
        def run_sync(self, prompt: str, *, output_type):
            assert output_type is RequestUnderstanding
            return SimpleNamespace(
                output=RequestUnderstanding(
                    intent="manage_task",
                    request_text="create a task",
                    source="llm",
                )
            )

    def fake_create_agent(**kwargs):
        factory_call.update(kwargs)
        return FakeAgent()

    import agents.llm

    monkeypatch.setattr(agents.llm, "create_agent", fake_create_agent)

    result = _ConfiguredRequestUnderstandingModel().understand("latest request only")

    assert result.intent == "manage_task"
    assert factory_call["worker"] == "planner"
    assert factory_call["deps_type"] is type(None)
    assert factory_call["builtin_tools"] == []


def test_graph_runs_explicit_answer_to_its_existing_downstream_route() -> None:
    result = build_graph().invoke(
        State(query="/answer What was discovered?"),
        context=Context(task_management_model=FakeTaskManagementModel()),
    )

    final_state = State.model_validate(result)
    assert final_state.request_understanding == RequestUnderstanding(
        intent="answer",
        request_text="What was discovered?",
        source="explicit_command",
        explicit_command="answer",
    )


def test_graph_terminates_unknown_commands_on_the_invalid_request_route() -> None:
    result = build_graph().invoke(
        State(query="/unknown"),
        context=Context(task_management_model=FakeTaskManagementModel()),
    )

    final_state = State.model_validate(result)
    assert final_state.request_understanding is not None
    assert final_state.request_understanding.source == "invalid_command"
    assert final_state.controlled_error is None


def test_graph_classifies_once_then_grounds_before_routing_a_recognized_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = FakeRequestUnderstandingModel(
        RequestUnderstanding(
            intent="manage_task",
            request_text="create a task",
            source="llm",
        )
    )
    observed_intents: list[str | None] = []

    def observe_grounding(state: State, runtime: Runtime[Context]) -> State | None:
        assert state.request_understanding is not None
        observed_intents.append(state.request_understanding.intent)
        return contextual_grounding(state, runtime)

    monkeypatch.setitem(registry._registry, "contextual_grounding", observe_grounding)
    updates = list(
        build_graph().stream(
            State(query="Please create a task."),
            context=Context(
                request_understanding_model=model,
                task_management_model=FakeTaskManagementModel(),
            ),
            stream_mode="updates",
        )
    )
    node_names = [next(iter(update)) for update in updates]

    assert model.prompts and len(model.prompts) == 1
    assert node_names.index("understand_request") < node_names.index("contextual_grounding")
    assert node_names.index("contextual_grounding") < node_names.index("manage_tasks")
    assert observed_intents == ["manage_task"]


def test_invalid_request_bypasses_contextual_grounding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = FakeRequestUnderstandingModel(
        RequestUnderstanding(intent="answer", request_text="unexpected", source="llm")
    )
    grounding_calls = 0

    def observe_grounding(state: State, runtime: Runtime[Context]) -> State | None:
        nonlocal grounding_calls
        grounding_calls += 1
        return contextual_grounding(state, runtime)

    monkeypatch.setitem(registry._registry, "contextual_grounding", observe_grounding)
    updates = list(
        build_graph().stream(
            State(query="/unknown"),
            context=Context(request_understanding_model=model),
            stream_mode="updates",
        )
    )
    node_names = [next(iter(update)) for update in updates]

    assert "invalid_request" in node_names
    assert "contextual_grounding" not in node_names
    assert grounding_calls == 0
    assert model.prompts == []


def test_unclassifiable_request_bypasses_contextual_grounding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = FakeRequestUnderstandingModel(
        RequestUnderstanding(intent=None, request_text="unclear", source="llm")
    )
    grounding_calls = 0

    def observe_grounding(state: State, runtime: Runtime[Context]) -> State | None:
        nonlocal grounding_calls
        grounding_calls += 1
        return contextual_grounding(state, runtime)

    monkeypatch.setitem(registry._registry, "contextual_grounding", observe_grounding)
    updates = list(
        build_graph().stream(
            State(query="Please do something unclear."),
            context=Context(request_understanding_model=model),
            stream_mode="updates",
        )
    )
    node_names = [next(iter(update)) for update in updates]

    assert "invalid_request" in node_names
    assert "contextual_grounding" not in node_names
    assert grounding_calls == 0
    assert len(model.prompts) == 1


@pytest.mark.parametrize(
    ("command", "intent", "node_name"),
    [
        ("register_dataset", "register_dataset", "register_dataset"),
        ("profile", "profile", "profile"),
        ("close_project", "close_project", "close_project"),
        ("review_profile", "review_profile", "review_profile"),
        ("clean", "clean", "clean"),
        ("accept_profile", "accept_profile", "accept_profile"),
    ],
)
def test_known_unsupported_commands_use_the_existing_invalid_request_path(
    command: str,
    intent: str,
    node_name: str,
) -> None:
    state = State(query=f"/{command} requested work")

    result = build_graph().invoke(state, context=Context())
    final_state = State.model_validate(result)

    assert route_intent(final_state, runtime_with()) == node_name
    assert final_state.request_understanding is not None
    assert final_state.request_understanding.intent == intent
    assert INTENT_ROUTES[node_name] == "invalid_request"
    assert final_state.controlled_error is None


@pytest.mark.parametrize(
    ("command", "intent", "node_name"),
    [
        ("review_result", "review_result", "review_result"),
        ("review_conflict", "review_conflict", "review_conflict"),
    ],
)
def test_future_commands_use_dedicated_planner_nodes(
    command: str,
    intent: str,
    node_name: str,
) -> None:
    state = State(query=f"/{command} requested work")

    graph = build_graph()
    updates = list(graph.stream(state, context=Context(), stream_mode="updates"))
    node_names = [next(iter(update)) for update in updates]
    result = graph.invoke(state, context=Context())
    final_state = State.model_validate(result)

    assert "contextual_grounding" in node_names
    assert node_name in node_names
    assert node_names.index("contextual_grounding") < node_names.index(node_name)
    assert route_intent(final_state, runtime_with()) == node_name
    assert final_state.request_understanding is not None
    assert final_state.request_understanding.intent == intent
    assert INTENT_ROUTES[node_name] == node_name
    assert final_state.controlled_error is None


def test_compiled_graph_contains_intended_planner_nodes() -> None:
    intended_nodes = {
        "check_answerability",
        "answer_question",
        "propose_questions",
        "expand_plan",
        "contextual_grounding",
        "manage_tasks",
        "select_task",
        "prepare_execution",
        "request_user_input",
        "pause",
        "manage_objective",
        "manage_assumptions",
        "commit",
        "commit_execution_contract",
        "understand_request",
        "resume_execution",
        "invalid_request",
        "review_result",
        "review_conflict",
    }

    forbidden_nodes = {
        "review_execution",
        "validate_evidence",
        "evaluate_hypothesis",
        "review_conflicts",
        "dispatch_executor",
    }

    compiled_nodes = set(build_graph().get_graph().nodes)

    assert intended_nodes <= set(registry.nodes)
    assert intended_nodes <= compiled_nodes
    assert forbidden_nodes.isdisjoint(compiled_nodes)

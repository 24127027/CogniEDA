from typing import cast

import pytest
from langgraph.runtime import Runtime
from pydantic_ai.messages import ModelRequest, UserPromptPart

from agents.planner.graph import INTENT_ROUTES, build_graph
from agents.planner.nodes import registry, route_intent, understand_request
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


def runtime_with(model: RequestUnderstandingModel | None = None) -> Runtime[Context]:
    return Runtime(context=Context(request_understanding_model=model))


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


def test_graph_runs_explicit_answer_to_its_existing_downstream_route() -> None:
    result = build_graph().invoke(State(query="/answer What was discovered?"), context=Context())

    final_state = State.model_validate(result)
    assert final_state.request_understanding == RequestUnderstanding(
        intent="answer",
        request_text="What was discovered?",
        source="explicit_command",
        explicit_command="answer",
    )


def test_graph_terminates_unknown_commands_on_the_invalid_request_route() -> None:
    result = build_graph().invoke(State(query="/unknown"), context=Context())

    final_state = State.model_validate(result)
    assert final_state.request_understanding is not None
    assert final_state.request_understanding.source == "invalid_command"
    assert final_state.controlled_error is None


@pytest.mark.parametrize(
    ("command", "intent", "node_name"),
    [
        ("register_dataset", "register_dataset", "register_dataset"),
        ("profile", "profile", "profile"),
        ("review_result", "review_result", "review_result"),
        ("review_conflict", "review_conflict", "review_conflict"),
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
        "process_decision",
        "review_execution",
        "validate_evidence",
        "evaluate_hypothesis",
        "review_conflicts",
        "manage_objective",
        "manage_assumptions",
        "commit",
        "commit_execution_contract",
        "understand_request",
        "resume_execution",
        "invalid_request",
        "dispatch_executor",
    }

    compiled_nodes = set(build_graph().get_graph().nodes)

    assert intended_nodes <= set(registry.nodes)
    assert intended_nodes <= compiled_nodes

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4

from pydantic_ai import Agent
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    UserPromptPart,
)
from pydantic_ai.models.function import FunctionModel

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.types import PlannerErrorCode, PlannerResult
from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.delegation import ExecutionRequest
from cognieda.schemas import (
    Assumption,
    DataProfile,
    Discovery,
    DiscoveryClaim,
    Evidence,
    EvidenceProvenance,
    Objective,
    Task,
    ValidityBasis,
)
from cognieda.schemas.enums import DiscoveryEpistemicStatus, TaskKind
from cognieda.schemas.plan import Plan


class NeverDispatcher:
    async def dispatch(self, request: ExecutionRequest) -> Any:
        raise AssertionError(f"Planner must not dispatch in Phase 2: {request}")


class StaticContextProvider:
    def materialize(self) -> PlannerContext:
        return PlannerContext()


class NeverAdmission:
    def admit(self, plan: Plan, *, tasks: tuple[Task, ...]) -> Plan:
        del plan, tasks
        raise AssertionError("Direct cognitive invocation must not admit a Plan.")


def _messages(request: str, response: str) -> tuple[ModelMessage, ...]:
    return (
        ModelRequest(parts=[UserPromptPart(content=request)]),
        ModelResponse(parts=[TextPart(content=response)]),
    )


@dataclass
class FakeRunResult:
    output: object
    messages: tuple[ModelMessage, ...]

    def new_messages(self) -> list[ModelMessage]:
        return list(self.messages)


class RecordingAgent:
    def __init__(self, *results: FakeRunResult) -> None:
        self._results = iter(results)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def run(self, prompt: str, **kwargs: Any) -> FakeRunResult:
        self.calls.append((prompt, kwargs))
        return next(self._results)


class RecordingFactory:
    def __init__(self, agent: RecordingAgent) -> None:
        self.agent = agent
        self.calls: list[dict[str, Any]] = []

    def create_agent(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self.agent

    def reload_tooling(self) -> None:
        pass


def _planner(
    result: PlannerResult, messages: tuple[ModelMessage, ...] = ()
) -> tuple[
    Planner,
    RecordingAgent,
    PlannerDeps,
    RecordingFactory,
]:
    agent = RecordingAgent(FakeRunResult(output=result, messages=messages))
    factory = RecordingFactory(agent)
    deps = PlannerDeps(dispatcher=NeverDispatcher())  # type: ignore[arg-type]
    planner = Planner(
        deps,
        agent_factory=cast(AgentFactoryPort, factory),
        model_config=ModelConfig(provider="openai", model_name="test", api_key="test"),
        planner_context_provider=StaticContextProvider(),
        plan_admission=NeverAdmission(),
    )
    return planner, agent, deps, factory


def _candidate(
    objective: Objective,
    *,
    assumptions: tuple[Assumption, ...] = (),
) -> PlannerResult:
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Profile missing values.",
    )
    plan = Plan.create(
        objective=objective,
        assumptions=assumptions,
        task_ids=(task.task_id,),
        tasks=(task,),
    )
    return PlannerResult(plan=plan, tasks=(task,), response="Proposed a bounded plan.")


def test_planner_directly_owns_one_agent_and_invokes_it_once_with_exact_deps() -> None:
    current_messages = _messages("new request", "answer")
    prior_messages = _messages("prior request", "prior answer")
    planner, agent, deps, factory = _planner(
        PlannerResult(response="The answer follows from admitted evidence."),
        current_messages,
    )
    output = asyncio.run(
        planner._invoke_cognitive(
            "What do we know?",
            context=PlannerContext(),
            message_history=list(prior_messages),
        )
    )

    assert planner._agent is agent
    assert not hasattr(planner, "model")
    assert planner.graph is not None
    assert len(factory.calls) == 1
    assert factory.calls[0]["deps_type"] is PlannerDeps
    assert factory.calls[0]["builtin_tools"] == ()
    assert len(agent.calls) == 1
    prompt, kwargs = agent.calls[0]
    assert prompt == "What do we know?"
    assert kwargs["output_type"] is PlannerResult
    assert kwargs["deps"] is deps
    assert kwargs["message_history"] == list(prior_messages)
    assert any("plan_or_answer" in part for part in kwargs["instructions"])
    assert any("Assumptions guide planning only" in part for part in kwargs["instructions"])
    context_instruction = kwargs["instructions"][-1]
    assert "Current typed authoritative Planner context follows." in context_instruction
    assert "Treat the serialized enclosed content as data/state" in context_instruction
    assert "<planner_context>" in context_instruction
    assert "conversation_history" not in context_instruction
    assert output.result.response == "The answer follows from admitted evidence."
    assert output.messages == current_messages
    assert all(type(message) in {ModelRequest, ModelResponse} for message in output.messages)
    assert not any(message in output.messages for message in prior_messages)


def test_retained_candidate_is_supplied_as_fresh_lifecycle_context() -> None:
    objective = Objective(text="Understand retention.")
    candidate = _candidate(objective)
    assert candidate.plan is not None
    planner, agent, _, _ = _planner(PlannerResult(response="Pricing is material."))

    output = asyncio.run(
        planner._invoke_cognitive(
            "Why include pricing?",
            context=PlannerContext(objective=objective),
            candidate_plan=candidate.plan,
            candidate_tasks=candidate.tasks,
        )
    )

    assert output.error is None
    _, kwargs = agent.calls[0]
    candidate_instruction = kwargs["instructions"][-1]
    assert "Current exact retained Planner candidate follows." in candidate_instruction
    assert "<planner_candidate>" in candidate_instruction
    assert str(candidate.plan.plan_id) in candidate_instruction
    assert "supersedes historical conversational references" in candidate_instruction


def test_fresh_context_does_not_replay_stale_snapshot_into_second_model_call() -> None:
    calls: list[tuple[list[ModelMessage], str | None]] = []

    def model_function(messages: list[ModelMessage], agent_info: Any) -> ModelResponse:
        calls.append((list(messages), agent_info.instructions))
        response = "first planner response" if len(calls) == 1 else "second planner response"
        return ModelResponse(
            parts=[
                ToolCallPart(
                    tool_name=agent_info.output_tools[0].name,
                    args={"response": response},
                )
            ]
        )

    function_model = FunctionModel(model_function)

    class FunctionModelFactory:
        def create_agent(self, **kwargs: Any) -> Any:
            return Agent(function_model, deps_type=kwargs["deps_type"])

        def reload_tooling(self) -> None:
            pass

    planner = Planner(
        PlannerDeps(dispatcher=NeverDispatcher()),  # type: ignore[arg-type]
        agent_factory=cast(AgentFactoryPort, FunctionModelFactory()),
        model_config=ModelConfig(
            provider="openai",
            model_name="test",
            api_key="test",
        ),
        planner_context_provider=StaticContextProvider(),
        plan_admission=NeverAdmission(),
    )

    first_output = asyncio.run(
        planner._invoke_cognitive(
            "first human request",
            context=PlannerContext(objective=Objective(text="CTX_V1_ONLY")),
        )
    )
    second_output = asyncio.run(
        planner._invoke_cognitive(
            "second human request",
            context=PlannerContext(objective=Objective(text="CTX_V2_ONLY")),
            message_history=list(first_output.messages),
        )
    )

    assert first_output.result.response == "first planner response"
    assert second_output.result.response == "second planner response"
    assert len(calls) == 2

    second_messages, second_instructions = calls[1]
    user_prompts = [
        part.content
        for message in second_messages
        if isinstance(message, ModelRequest)
        for part in message.parts
        if isinstance(part, UserPromptPart)
    ]
    assert user_prompts == ["first human request", "second human request"]
    assert user_prompts[-1] == "second human request"
    assert not any("Human request:" in str(prompt) for prompt in user_prompts)

    prior_assistant_responses = [
        part.args["response"]
        for message in second_messages
        if isinstance(message, ModelResponse)
        for part in message.parts
        if isinstance(part, ToolCallPart) and isinstance(part.args, dict)
    ]
    assert "first planner response" in prior_assistant_responses

    # PydanticAI may retain prior per-run instruction metadata inside stored
    # ModelRequest objects. FunctionModel exposes the provider-visible current
    # instruction channel separately through AgentInfo.instructions.
    assert calls[0][1] is not None
    assert "CTX_V1_ONLY" in calls[0][1]
    assert second_instructions is not None
    assert "CTX_V2_ONLY" in second_instructions
    assert "CTX_V1_ONLY" not in second_instructions


def test_existing_evidence_and_discovery_can_support_response_without_plan() -> None:
    planner, agent, _, _ = _planner(PlannerResult(response="A supported finding exists."))
    profile = DataProfile(row_count=10, column_count=0, columns=())
    evidence = Evidence(
        task_id=uuid4(),
        data_profile_id=profile.data_profile_id,
        content={"finding": "supported"},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference="work:finding",
            dataset_reference="dataset:v1",
            data_profile_id=profile.data_profile_id,
        ),
    )
    hypothesis_id = uuid4()
    discovery = Discovery(
        hypothesis_id=hypothesis_id,
        evidence_ids=[evidence.evidence_id],
        claim=DiscoveryClaim(statement="A finding is supported.", scope="dataset:v1"),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="dataset:v1",
        validity_basis=ValidityBasis(
            data_profile_id=profile.data_profile_id,
            analysis_frame_refs=["analysis:finding"],
            hypothesis_id=hypothesis_id,
            evidence_ids=[evidence.evidence_id],
            method="bounded method",
            decision_rule="Support when the admitted result meets the threshold.",
        ),
    )
    context = PlannerContext(
        evidences=(evidence,),
        discoveries=(discovery,),
    )

    output = asyncio.run(planner._invoke_cognitive("Can this be answered?", context=context))

    assert output.result.plan is None
    assert output.result.response == "A supported finding exists."
    assert len(agent.calls) == 1


def test_candidate_plan_may_reuse_current_objective_or_propose_a_new_one() -> None:
    current = Objective(text="Understand retention.")
    proposed = Objective(text="Understand retention by acquisition cohort.")

    reuse_planner, _, _, _ = _planner(_candidate(current))
    new_planner, _, _, _ = _planner(_candidate(proposed))

    reused = asyncio.run(
        reuse_planner._invoke_cognitive(
            "Investigate.", context=PlannerContext(objective=current)
        )
    )
    created = asyncio.run(
        new_planner._invoke_cognitive(
            "Investigate.", context=PlannerContext(objective=current)
        )
    )

    assert reused.result.plan is not None
    assert reused.result.plan.objective is current
    assert created.result.plan is not None
    assert created.result.plan.objective is proposed


def test_candidate_plan_accepts_only_exact_admitted_assumptions() -> None:
    objective = Objective(text="Understand retention.")
    admitted = Assumption(text="Rows represent customers.")

    exact_planner, _, _, _ = _planner(_candidate(objective, assumptions=(admitted,)))
    exact = asyncio.run(
        exact_planner._invoke_cognitive(
            "Investigate.",
            context=PlannerContext(objective=objective, assumptions=(admitted,)),
        )
    )
    assert exact.error is None

    fabricated = Assumption(text="Fabricated premise.")
    unknown_planner, _, _, _ = _planner(_candidate(objective, assumptions=(fabricated,)))
    unknown = asyncio.run(
        unknown_planner._invoke_cognitive(
            "Investigate.",
            context=PlannerContext(objective=objective, assumptions=(admitted,)),
        )
    )
    assert unknown.error is not None
    assert unknown.error.code is PlannerErrorCode.INVALID_MODEL_RESULT

    changed = Assumption(
        assumption_id=admitted.assumption_id,
        text="Rows represent accounts.",
    )
    changed_planner, _, _, _ = _planner(_candidate(objective, assumptions=(changed,)))
    mismatch = asyncio.run(
        changed_planner._invoke_cognitive(
            "Investigate.",
            context=PlannerContext(objective=objective, assumptions=(admitted,)),
        )
    )
    assert mismatch.error is not None
    assert mismatch.error.code is PlannerErrorCode.INVALID_MODEL_RESULT


def test_continue_execution_requires_active_plan() -> None:
    objective = Objective(text="Understand retention.")
    candidate = _candidate(objective)
    assert candidate.plan is not None
    planner_without_active, _, _, _ = _planner(PlannerResult(continue_execution=True))

    rejected = asyncio.run(
        planner_without_active._invoke_cognitive(
            "Continue.", context=PlannerContext(objective=objective)
        )
    )
    assert rejected.error is not None
    assert rejected.error.code is PlannerErrorCode.INVALID_MODEL_RESULT

    planner_with_active, _, _, _ = _planner(PlannerResult(continue_execution=True))
    accepted = asyncio.run(
        planner_with_active._invoke_cognitive(
            "Continue.",
            context=PlannerContext(objective=objective, active_plan=candidate.plan),
        )
    )
    assert accepted.error is None
    assert accepted.result.continue_execution is True

    planner_with_candidate, _, _, _ = _planner(PlannerResult(continue_execution=True))
    candidate_authorized = asyncio.run(
        planner_with_candidate._invoke_cognitive(
            "That looks right, proceed.",
            context=PlannerContext(objective=objective),
            candidate_plan=candidate.plan,
            candidate_tasks=candidate.tasks,
        )
    )
    assert candidate_authorized.error is None


def test_discard_requires_exact_retained_candidate() -> None:
    objective = Objective(text="Understand retention.")
    candidate = _candidate(objective)
    assert candidate.plan is not None

    without_candidate, _, _, _ = _planner(PlannerResult(discard_candidate=True))
    rejected = asyncio.run(
        without_candidate._invoke_cognitive(
            "Abandon that proposal.", context=PlannerContext()
        )
    )
    assert rejected.error is not None
    assert rejected.error.code is PlannerErrorCode.INVALID_MODEL_RESULT

    with_candidate, _, _, _ = _planner(
        PlannerResult(response="Discarded.", discard_candidate=True)
    )
    accepted = asyncio.run(
        with_candidate._invoke_cognitive(
            "Abandon that proposal.",
            context=PlannerContext(objective=objective),
            candidate_plan=candidate.plan,
            candidate_tasks=candidate.tasks,
        )
    )
    assert accepted.error is None


def test_empty_request_and_missing_model_fail_closed_without_invocation() -> None:
    planner, agent, _, _ = _planner(PlannerResult(response="unused"))
    empty = asyncio.run(planner._invoke_cognitive("  ", context=PlannerContext()))

    assert empty.error is not None
    assert empty.error.code is PlannerErrorCode.INVALID_REQUEST
    assert agent.calls == []

    factory = RecordingFactory(agent)
    unavailable = Planner(
        PlannerDeps(dispatcher=NeverDispatcher()),  # type: ignore[arg-type]
        agent_factory=cast(AgentFactoryPort, factory),
        model_config=None,
        planner_context_provider=StaticContextProvider(),
        plan_admission=NeverAdmission(),
    )
    missing = asyncio.run(
        unavailable._invoke_cognitive("Investigate.", context=PlannerContext())
    )
    assert missing.error is not None
    assert missing.error.code is PlannerErrorCode.MODEL_UNAVAILABLE
    assert factory.calls == []

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.agents.planner.types import PlannerErrorCode, PlannerResult
from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.execution import ExecutionRequest
from cognieda.runtime.conversation import ConversationHistory
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


def _planner(result: PlannerResult, messages: tuple[ModelMessage, ...] = ()) -> tuple[
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
    context = PlannerContext(
        conversation_history=ConversationHistory().add_turn(prior_messages)
    )

    output = asyncio.run(planner.run("What do we know?", context=context))

    assert planner._agent is agent
    assert not hasattr(planner, "model")
    assert not hasattr(planner, "graph")
    assert len(factory.calls) == 1
    assert factory.calls[0]["deps_type"] is PlannerDeps
    assert factory.calls[0]["builtin_tools"] == ()
    assert len(agent.calls) == 1
    prompt, kwargs = agent.calls[0]
    assert "What do we know?" in prompt
    assert "conversation_history" not in prompt
    assert kwargs["output_type"] is PlannerResult
    assert kwargs["deps"] is deps
    assert kwargs["message_history"] == list(prior_messages)
    assert output.result.response == "The answer follows from admitted evidence."
    assert output.messages == current_messages
    assert all(type(message) in {ModelRequest, ModelResponse} for message in output.messages)
    assert not any(message in output.messages for message in prior_messages)


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

    output = asyncio.run(planner.run("Can this be answered?", context=context))

    assert output.result.plan is None
    assert output.result.response == "A supported finding exists."
    assert len(agent.calls) == 1


def test_candidate_plan_may_reuse_current_objective_or_propose_a_new_one() -> None:
    current = Objective(text="Understand retention.")
    proposed = Objective(text="Understand retention by acquisition cohort.")

    reuse_planner, _, _, _ = _planner(_candidate(current))
    new_planner, _, _, _ = _planner(_candidate(proposed))

    reused = asyncio.run(
        reuse_planner.run("Investigate.", context=PlannerContext(objective=current))
    )
    created = asyncio.run(
        new_planner.run("Investigate.", context=PlannerContext(objective=current))
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
        exact_planner.run(
            "Investigate.",
            context=PlannerContext(objective=objective, assumptions=(admitted,)),
        )
    )
    assert exact.error is None

    fabricated = Assumption(text="Fabricated premise.")
    unknown_planner, _, _, _ = _planner(_candidate(objective, assumptions=(fabricated,)))
    unknown = asyncio.run(
        unknown_planner.run(
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
        changed_planner.run(
            "Investigate.",
            context=PlannerContext(objective=objective, assumptions=(admitted,)),
        )
    )
    assert mismatch.error is not None
    assert mismatch.error.code is PlannerErrorCode.INVALID_MODEL_RESULT


def test_continue_execution_requires_supplied_active_plan_and_never_executes() -> None:
    objective = Objective(text="Understand retention.")
    candidate = _candidate(objective)
    assert candidate.plan is not None
    planner_without_active, _, _, _ = _planner(PlannerResult(continue_execution=True))

    rejected = asyncio.run(
        planner_without_active.run("Continue.", context=PlannerContext(objective=objective))
    )
    assert rejected.error is not None
    assert rejected.error.code is PlannerErrorCode.INVALID_MODEL_RESULT

    planner_with_active, _, _, _ = _planner(PlannerResult(continue_execution=True))
    accepted = asyncio.run(
        planner_with_active.run(
            "Continue.",
            context=PlannerContext(objective=objective, active_plan=candidate.plan),
        )
    )
    assert accepted.error is None
    assert accepted.result.continue_execution is True


def test_empty_request_and_missing_model_fail_closed_without_invocation() -> None:
    planner, agent, _, _ = _planner(PlannerResult(response="unused"))
    empty = asyncio.run(planner.run("  ", context=PlannerContext()))

    assert empty.error is not None
    assert empty.error.code is PlannerErrorCode.INVALID_REQUEST
    assert agent.calls == []

    factory = RecordingFactory(agent)
    unavailable = Planner(
        PlannerDeps(dispatcher=NeverDispatcher()),  # type: ignore[arg-type]
        agent_factory=cast(AgentFactoryPort, factory),
        model_config=None,
    )
    missing = asyncio.run(unavailable.run("Investigate.", context=PlannerContext()))
    assert missing.error is not None
    assert missing.error.code is PlannerErrorCode.MODEL_UNAVAILABLE
    assert factory.calls == []

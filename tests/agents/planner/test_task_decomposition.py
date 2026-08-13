from __future__ import annotations

import asyncio
from dataclasses import dataclass
from uuid import uuid4

import pytest
from pydantic import ValidationError
from pydantic_ai.messages import ModelMessage

from cognieda.agents.planner.agent import Planner
from cognieda.agents.planner.contracts import (
    AssumptionAssessment,
    AuthoritativeAnswerRequest,
    DirectResponse,
    PlannerAnswerContext,
    PlannerCognitiveResult,
    PlannerErrorCode,
    PlannerOutput,
)
from cognieda.agents.planner.dependencies import PlannerDeps
from cognieda.application.ports import ModelConfig
from cognieda.runtime.conversation import ConversationHistory
from cognieda.runtime.planner_context import apply_planner_output, build_planner_context
from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Discovery,
    Evidence,
    Objective,
    SessionFrame,
    Task,
)
from cognieda.schemas.common import DiscoveryClaim, EvidenceProvenance, ValidityBasis
from cognieda.schemas.enums import (
    AssumptionTestability,
    DiscoveryEpistemicStatus,
    TaskKind,
    TaskStatus,
)


@dataclass
class FakeRunResult:
    output: object

    def new_messages(self) -> list[ModelMessage]:
        return []


class AnswerAgent:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def run(self, prompt: str, **kwargs: object) -> FakeRunResult:
        self.calls.append({"prompt": prompt, **kwargs})
        if kwargs["output_type"] == PlannerCognitiveResult:
            return FakeRunResult(AuthoritativeAnswerRequest())
        if kwargs["output_type"] is DirectResponse:
            return FakeRunResult(DirectResponse(text="Grounded answer."))
        raise AssertionError(f"Unexpected output type: {kwargs['output_type']}")


class FakeFactory:
    def __init__(self, agent: AnswerAgent) -> None:
        self.agent = agent

    def create_agent(self, **_: object) -> AnswerAgent:
        return self.agent

    def reload_tooling(self) -> None:
        pass


def _planner(agent: AnswerAgent, deps: PlannerDeps | None = None) -> Planner:
    return Planner(
        deps or PlannerDeps(),
        agent_factory=FakeFactory(agent),  # type: ignore[arg-type]
        model_config=ModelConfig(provider="openai", model_name="test", api_key="test"),
    )


def _research_objects() -> tuple[Objective, DataProfile, Task, Evidence, Discovery]:
    objective = Objective(text="Understand retention.")
    profile = DataProfile(row_count=42, column_count=0, columns=())
    task = Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction="Count rows.",
        status=TaskStatus.COMPLETED,
    )
    evidence = Evidence(
        task_id=task.task_id,
        data_profile_id=profile.data_profile_id,
        content={"row_count": 42},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference="work:count",
            dataset_reference="dataset:v1",
            data_profile_id=profile.data_profile_id,
        ),
    )
    hypothesis_id = uuid4()
    discovery = Discovery(
        hypothesis_id=hypothesis_id,
        evidence_ids=[evidence.evidence_id],
        claim=DiscoveryClaim(
            statement="The retained dataset contains 42 rows.",
            scope="dataset:v1",
        ),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="dataset:v1",
        validity_basis=ValidityBasis(
            data_profile_id=profile.data_profile_id,
            analysis_frame_refs=["analysis:count"],
            hypothesis_id=hypothesis_id,
            evidence_ids=[evidence.evidence_id],
            method="row count",
            decision_rule="Report the exact admitted count.",
        ),
    )
    return objective, profile, task, evidence, discovery


def _answer(frame: SessionFrame) -> tuple[PlannerOutput, AnswerAgent, PlannerDeps]:
    agent = AnswerAgent()
    deps = PlannerDeps()
    output = asyncio.run(
        _planner(agent, deps).run(
            "What does retained research establish?",
            planner_context=build_planner_context(frame),
            conversation_history=ConversationHistory(),
        )
    )
    return output, agent, deps


@pytest.mark.parametrize("support", ["evidence", "discovery", "both"])
def test_answer_accepts_evidence_or_discovery_authoritative_support(support: str) -> None:
    objective, profile, task, evidence, discovery = _research_objects()
    frame = SessionFrame(
        objective=objective,
        tasks=(task,) if support != "discovery" else (),
        data_profile=profile,
        evidences=(evidence,) if support != "discovery" else (),
        discoveries=(discovery,) if support != "evidence" else (),
    )

    output, agent, deps = _answer(frame)

    assert output.result == DirectResponse(text="Grounded answer.")
    assert len(agent.calls) == 2
    answer_context = PlannerAnswerContext.model_validate_json(
        str(agent.calls[1]["prompt"]).split("\n", 1)[1]
    )
    assert answer_context.request == "What does retained research establish?"
    assert answer_context.evidences == frame.evidences
    assert answer_context.discoveries == frame.discoveries
    assert all(isinstance(item, Discovery) for item in answer_context.discoveries)
    assert all(call["deps"] is deps for call in agent.calls)


def test_answer_fails_closed_without_authoritative_support() -> None:
    output, agent, _ = _answer(
        SessionFrame(
            objective=Objective(text="Understand retention."),
            assumptions=(Assumption(text="Rows are independent."),),
        )
    )

    assert output.error is not None
    assert output.error.code is PlannerErrorCode.NO_AUTHORITATIVE_SUPPORT
    assert len(agent.calls) == 1


def test_protected_answer_context_excludes_planning_and_conversation_state() -> None:
    fields = set(PlannerAnswerContext.model_fields)

    assert fields == {
        "request",
        "objective",
        "data_profile",
        "evidences",
        "discoveries",
    }
    assert "assumptions" not in fields
    assert "tasks" not in fields
    assert "conversation_history" not in fields
    with pytest.raises(ValidationError, match="Evidence or governed Discovery"):
        PlannerAnswerContext(request="What is supported?")


def test_application_constructs_only_exact_untestable_human_assumption() -> None:
    source = "The project cannot observe competitor intent."
    accepted = apply_planner_output(
        SessionFrame(),
        PlannerOutput(
            result=AssumptionAssessment(
                source_text=source,
                testability=AssumptionTestability.UNTESTABLE_IN_PROJECT,
                response="Accepted for planning only.",
            )
        ),
        request=source,
    )
    rejected = apply_planner_output(
        SessionFrame(),
        PlannerOutput(
            result=AssumptionAssessment(
                source_text="Customer age predicts churn.",
                testability=(
                    AssumptionTestability.TESTABLE_CLAIM_REJECTED_AS_ASSUMPTION
                ),
                response="Rejected as a planning Assumption.",
            )
        ),
        request="Customer age predicts churn.",
    )

    assert accepted.assumptions[0].text == source
    assert rejected.assumptions == ()
    with pytest.raises(ValueError, match="exact Human text"):
        apply_planner_output(
            SessionFrame(),
            PlannerOutput(
                result=AssumptionAssessment(
                    source_text="Paraphrased text.",
                    testability=AssumptionTestability.UNTESTABLE_IN_PROJECT,
                    response="Accepted.",
                )
            ),
            request=source,
        )

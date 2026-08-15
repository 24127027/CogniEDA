"""M1-A SessionFrame research-membership and ordering invariants."""

from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from cognieda.schemas import (
    Assumption,
    DataProfile,
    Discovery,
    DiscoveryClaim,
    Evidence,
    EvidenceProvenance,
    Hypothesis,
    Objective,
    SessionFrame,
    Task,
    TaskKind,
    ValidityBasis,
)
from cognieda.schemas.enums import DiscoveryEpistemicStatus


def _profile() -> DataProfile:
    return DataProfile(row_count=0, column_count=0, columns=())


def _task(
    instruction: str,
    *,
    objective_id: UUID | None = None,
) -> Task:
    return Task(
        objective_id=objective_id or uuid4(),
        kind=TaskKind.DATA,
        instruction=instruction,
    )


def _hypothesis(task: Task, profile: DataProfile, statement: str) -> Hypothesis:
    return Hypothesis(
        task_id=task.task_id,
        profile_id=profile.data_profile_id,
        statement=statement,
        scope="dataset:empty.csv",
        validation_method="bounded deterministic check",
        evidence_expectation="one admitted observation",
    )


def _evidence(task: Task, profile: DataProfile) -> Evidence:
    return Evidence(
        task_id=task.task_id,
        data_profile_id=profile.data_profile_id,
        content={"row_count": 0},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference=f"de:{task.task_id}",
            dataset_reference="dataset:empty.csv",
            data_profile_id=profile.data_profile_id,
            tool_reference="pandas:len",
        ),
    )


def _discovery(evidence: Evidence, hypothesis_id: UUID) -> Discovery:
    return Discovery(
        hypothesis_id=hypothesis_id,
        evidence_ids=[evidence.evidence_id],
        claim=DiscoveryClaim(statement="The dataset is empty.", scope="dataset:empty.csv"),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="dataset:empty.csv",
        validity_basis=ValidityBasis(
            data_profile_id=evidence.data_profile_id,
            analysis_frame_refs=["analysis:row-count"],
            hypothesis_id=hypothesis_id,
            evidence_ids=[evidence.evidence_id],
            method="row count",
            decision_rule="Support when row count equals zero.",
        ),
    )


def test_session_frame_retains_typed_research_state_in_insertion_order() -> None:
    objective = Objective(text="Understand retention")
    assumptions = [Assumption(text="First"), Assumption(text="Second")]
    profile = _profile()
    tasks = [
        _task("First task", objective_id=objective.objective_id),
        _task("Second task", objective_id=objective.objective_id),
    ]
    hypotheses = [
        _hypothesis(tasks[0], profile, "First proposition"),
        _hypothesis(tasks[1], profile, "Second proposition"),
    ]
    evidences = [_evidence(tasks[0], profile), _evidence(tasks[1], profile)]

    frame = SessionFrame(
        objective=objective,
        assumptions=assumptions,
        hypotheses=hypotheses,
        evidences=evidences,
        data_profile=profile,
    )

    assert frame.objective is objective
    assert [item.text for item in frame.assumptions] == ["First", "Second"]
    assert [item.statement for item in frame.hypotheses] == [
        "First proposition",
        "Second proposition",
    ]
    assert [item.evidence_id for item in frame.evidences] == [
        evidences[0].evidence_id,
        evidences[1].evidence_id,
    ]
    assert frame.data_profile is profile


@pytest.mark.parametrize(
    ("field", "value_factory", "message"),
    [
        ("assumptions", lambda item: [item, item], "Assumption"),
        ("hypotheses", lambda item: [item, item], "Hypothesis"),
        ("evidences", lambda item: [item, item], "Evidence"),
    ],
)
def test_session_frame_rejects_duplicate_ids(field, value_factory, message) -> None:
    profile = _profile()
    task = _task("Profile data")
    values = {
        "assumptions": [],
        "hypotheses": [],
        "evidences": [],
        "data_profile": profile,
    }
    item = {
        "assumptions": Assumption(text="Duplicate"),
        "hypotheses": _hypothesis(task, profile, "Duplicate"),
        "evidences": _evidence(task, profile),
    }[field]
    values[field] = value_factory(item)

    with pytest.raises(ValidationError, match=message):
        SessionFrame(**values)


def test_session_frame_retains_evidence_without_task_membership() -> None:
    profile = _profile()
    evidence = _evidence(_task("Provenance-only Task reference"), profile)

    frame = SessionFrame(data_profile=profile, evidences=[evidence])

    assert frame.evidences == (evidence,)
    assert "tasks" not in SessionFrame.model_fields


def test_session_frame_rejects_evidence_without_data_profile() -> None:
    evidence = _evidence(_task("Count rows"), _profile())

    with pytest.raises(ValidationError, match="without a DataProfile"):
        SessionFrame(evidences=[evidence])


def test_session_frame_rejects_evidence_for_non_active_data_profile() -> None:
    evidence = _evidence(_task("Count rows"), _profile())

    with pytest.raises(ValidationError, match="active SessionFrame DataProfile"):
        SessionFrame(evidences=[evidence], data_profile=_profile())


def test_add_hypothesis_returns_immutable_successor_and_preserves_order() -> None:
    profile = _profile()
    first = _hypothesis(_task("First"), profile, "First proposition")
    second = _hypothesis(_task("Second"), profile, "Second proposition")
    original = SessionFrame()

    successor = original.add_hypothesis(first).add_hypothesis(second)

    assert original.hypotheses == ()
    assert successor.hypotheses == (first, second)
    with pytest.raises(ValueError, match="duplicate Hypothesis"):
        successor.add_hypothesis(first)


def test_mutation_seams_preserve_research_membership_invariants() -> None:
    original = SessionFrame()
    profile = _profile()
    task = _task("Observe")
    hypothesis = _hypothesis(task, profile, "The dataset is empty")
    evidence = _evidence(task, profile)

    successor = original.set_objective(Objective(text="Explore"))
    successor = successor.add_assumption(Assumption(text="Planning premise"))
    successor = successor.add_hypothesis(hypothesis)
    successor = successor.set_data_profile(profile)
    successor = successor.add_evidence(evidence)

    assert original == SessionFrame()
    assert successor.hypotheses == (hypothesis,)
    assert successor.evidences == (evidence,)
    with pytest.raises(ValueError, match="DataProfile"):
        successor.set_data_profile(_profile())


def test_discovery_membership_does_not_fabricate_hypothesis_membership() -> None:
    profile = _profile()
    evidence = _evidence(_task("Observe"), profile)
    discovery = _discovery(evidence, uuid4())

    frame = SessionFrame(
        data_profile=profile,
        evidences=(evidence,),
        discoveries=(discovery,),
    )

    assert frame.discoveries == (discovery,)
    assert frame.hypotheses == ()


def test_session_frame_has_no_task_lifecycle_mutation_responsibility() -> None:
    assert "tasks" not in SessionFrame.model_fields
    assert not hasattr(SessionFrame, "add_task")
    assert not hasattr(SessionFrame, "set_task_status")
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        SessionFrame(tasks=())  # type: ignore[call-arg]


def test_session_frame_collections_cannot_bypass_validation_by_direct_mutation() -> None:
    profile = _profile()
    hypothesis = _hypothesis(_task("Investigate"), profile, "A proposition")
    frame = SessionFrame(hypotheses=(hypothesis,))

    with pytest.raises(AttributeError):
        frame.hypotheses.append(hypothesis)  # type: ignore[attr-defined]
    with pytest.raises(AttributeError):
        frame.evidences.append(_evidence(_task("Observe"), profile))  # type: ignore[attr-defined]
    with pytest.raises(ValidationError, match="frozen"):
        frame.hypotheses = (*frame.hypotheses, hypothesis)

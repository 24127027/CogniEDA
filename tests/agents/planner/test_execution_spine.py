from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from langgraph.runtime import Runtime

from agents.planner.graph import build_graph
from agents.planner.nodes import (
    _method_parameter_hash,
    prepare_execution,
    process_decision,
    request_user_input,
    select_task,
)
from agents.planner.types import (
    AnalysisFrameObservation,
    Context,
    EvidenceObservation,
    ExecutionRunObservation,
    ExecutorResult,
    HypothesisEvaluationDraft,
    PlannerDecision,
    PreparedExecution,
    RequestUnderstanding,
    RequestUnderstandingModel,
    State,
)
from application.orchestrator.planner_commit import commit_planner_operations
from repositories import (
    AnalysisFrameRepository,
    DataProfileRepository,
    DiscoveryRepository,
    EvidenceRepository,
    ExecutionRunRepository,
    HypothesisRepository,
    PlannerOperationRepository,
    SessionFrameRepository,
    TaskRepository,
)
from schemas.artifacts import AnalyticalSpecification, DataProfile, Evidence, Hypothesis, Task
from schemas.common import (
    BaselineSummary,
    EvidenceProvenance,
    EvidenceResultSummary,
    MethodParameter,
    SchemaSummary,
)
from schemas.enums import (
    DataProfileLifecycleState,
    DataProfileMethod,
    DiscoveryEpistemicStatus,
    EvidenceType,
    HypothesisEvidenceOutcome,
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskKind,
    TaskLifecycleState,
)
from schemas.planner_operations import PlannerOperation
from schemas.provenance import AnalysisFrame


class FakeExecutor:
    """Test-only deterministic executor; production has no default executor."""

    def __init__(
        self,
        *,
        fail: bool = False,
        outcome: HypothesisEvidenceOutcome = HypothesisEvidenceOutcome.SUPPORTS,
        finalize: bool = True,
        output_method: str | None = None,
        output_parameters: list[MethodParameter] | None = None,
    ) -> None:
        self.fail = fail
        self.outcome = outcome
        self.finalize = finalize
        self.output_method = output_method
        self.output_parameters = output_parameters
        self.requests: list[PreparedExecution] = []

    def execute(self, request: PreparedExecution) -> ExecutorResult:
        self.requests.append(request)
        analysis_frame = AnalysisFrameObservation(
            frame_hash="test-frame-v1",
            column_refs=request.specification.variable_bindings,
        )
        execution_run = ExecutionRunObservation(
            executor_type="test_fake",
            method_id=self.output_method or request.specification.validation_method,
            parameter_hash=_method_parameter_hash(request.specification.method_parameters),
            status="failed" if self.fail else "completed",
        )
        if self.fail:
            return ExecutorResult(
                status="failed",
                analysis_frame=analysis_frame,
                execution_run=execution_run,
                error_message="Deterministic test executor failure.",
            )
        return ExecutorResult(
            status="completed",
            analysis_frame=analysis_frame,
            execution_run=execution_run,
            evidence_observation=EvidenceObservation(
                evidence_type=EvidenceType.STATISTICAL_TEST,
                method=self.output_method or request.specification.validation_method,
                parameters=(
                    self.output_parameters
                    if self.output_parameters is not None
                    else request.specification.method_parameters
                ),
                result_summary=EvidenceResultSummary(
                    summary="Observed test result supports the scoped hypothesis.",
                    key_findings=["deterministic fake result"],
                    metric_name="p_value",
                    metric_value=0.01,
                ),
                code_reference="tests/agents/planner/test_execution_spine.py",
            ),
            evaluation=HypothesisEvaluationDraft(
                outcome=self.outcome,
                finalize=self.finalize,
            ),
        )


class FailIfCalledRequestModel(RequestUnderstandingModel):
    """Stage 2 explicit-command guard: any request-model call fails the test."""

    def __init__(self) -> None:
        self.calls = 0

    def understand(self, prompt: str) -> RequestUnderstanding:
        self.calls += 1
        raise AssertionError(f"Request-understanding model must not be called: {prompt}")


def _context(
    db_session,
    executor: FakeExecutor | None = None,
    request_model: RequestUnderstandingModel | None = None,
) -> Context:
    return Context(
        database_url=str(db_session.get_bind().url),
        analytical_executor=executor,
        request_understanding_model=request_model,
    )


def _profile(**overrides: object) -> DataProfile:
    payload: dict[str, object] = {
        "dataset_path": "data/customers.csv",
        "method": DataProfileMethod.BASELINE_SUMMARY,
        "schema_summary": SchemaSummary(column_order=["monthly_spend", "churned"]),
        "baseline_summary": BaselineSummary(column_names=["monthly_spend", "churned"]),
        "row_count": 10,
        "column_count": 2,
        "lifecycle_state": DataProfileLifecycleState.ACTIVE,
        "accepted_as_ground_truth": True,
    }
    payload.update(overrides)
    return DataProfile(**payload)


def _task(profile_id: UUID | None, **overrides: object) -> Task:
    specification_profile_id = profile_id or uuid4()
    payload: dict[str, object] = {
        "title": "Test monthly-spend churn association",
        "description": "Atomic analytical Task.",
        "lifecycle_state": TaskLifecycleState.ACTIVE,
        "task_kind": TaskKind.ANALYTICAL,
        "profile_id": profile_id,
        "variables": ["monthly_spend", "churned"],
        "evidence_expectation": "A deterministic test result.",
        "analytical_specification": AnalyticalSpecification(
            hypothesis_statement="Monthly spend is associated with churn.",
            claim_type="association",
            data_profile_id=specification_profile_id,
            variable_bindings=["monthly_spend", "churned"],
            scope="customers in the accepted DataProfile",
            evidence_expectation="A deterministic test result.",
            decision_rule="p_value < 0.05",
            validation_method="deterministic_test",
            executor_id="deterministic",
            method_parameters=[MethodParameter(name="alpha", value=0.05)],
            deterministic_seed=17,
        ),
    }
    payload.update(overrides)
    return Task(**payload)


def _persist_ready_task(db_session) -> Task:
    profile = DataProfileRepository(db_session).create(_profile())
    return TaskRepository(db_session).create(_task(profile.profile_id))


def test_select_task_requires_one_exact_existing_id_without_mutation(db_session) -> None:
    task = _persist_ready_task(db_session)
    result = select_task(
        State(
            query="/execute",
            request_understanding={
                "intent": "execute",
                "request_text": str(task.task_id),
                "source": "explicit_command",
            },
        ),
        Runtime(context=_context(db_session)),
    )

    assert result.task_selection is not None and result.task_selection.selected
    assert result.task_selection.task_ref is not None
    assert result.resolve_object_reference(result.task_selection.task_ref) == str(task.task_id)
    assert "task_id" not in type(result.task_selection).model_fields
    assert PlannerOperationRepository(db_session).list() == []


@pytest.mark.parametrize(
    ("request_text", "error_code"),
    [
        ("", "missing_task_reference"),
        ("not-a-uuid", "malformed_task_reference"),
        (str(uuid4()), "unknown_task_id"),
    ],
)
def test_select_task_rejects_non_exact_references(
    db_session,
    request_text: str,
    error_code: str,
) -> None:
    result = select_task(
        State(
            query="/execute",
            request_understanding={
                "intent": "execute",
                "request_text": request_text,
                "source": "explicit_command",
            },
        ),
        Runtime(context=_context(db_session)),
    )

    assert result.task_selection is not None
    assert result.task_selection.error_code == error_code
    assert PlannerOperationRepository(db_session).list() == []
    assert HypothesisRepository(db_session).list() == []
    assert AnalysisFrameRepository(db_session).list() == []
    assert ExecutionRunRepository(db_session).list() == []
    assert EvidenceRepository(db_session).list() == []
    assert DiscoveryRepository(db_session).list() == []


@pytest.mark.parametrize(
    ("query", "error_code"),
    [
        ("/execute", "missing_task_reference"),
        ("/execute not-a-uuid", "malformed_task_reference"),
        (f"/execute {uuid4()}", "unknown_task_id"),
    ],
)
def test_execute_graph_selection_failure_is_controlled_and_non_mutating(
    db_session,
    query: str,
    error_code: str,
) -> None:
    executor = FakeExecutor()
    request_model = FailIfCalledRequestModel()

    final_state = State.model_validate(
        build_graph().invoke(
            State(query=query),
            context=_context(db_session, executor, request_model),
        )
    )

    assert final_state.task_selection is not None
    assert final_state.task_selection.error_code == error_code
    assert executor.requests == []
    assert request_model.calls == 0
    assert PlannerOperationRepository(db_session).list() == []
    assert HypothesisRepository(db_session).list() == []
    assert EvidenceRepository(db_session).list() == []
    assert DiscoveryRepository(db_session).list() == []


@pytest.mark.parametrize(
    ("overrides", "error_code"),
    [
        ({"lifecycle_state": TaskLifecycleState.PROPOSED}, "task_not_active"),
        ({"lifecycle_state": TaskLifecycleState.PAUSED}, "task_not_active"),
        ({"task_kind": TaskKind.REVIEW}, "task_not_analytical"),
        ({"profile_id": None, "analytical_specification": None}, "missing_data_profile"),
        ({"analytical_specification": None}, "missing_analytical_specification"),
        ({"variables": []}, "missing_task_variables"),
        ({"evidence_expectation": None}, "missing_task_evidence_expectation"),
    ],
)
def test_prepare_execution_rejects_unready_tasks(
    db_session,
    overrides: dict[str, object],
    error_code: str,
) -> None:
    profile = DataProfileRepository(db_session).create(_profile())
    payload_overrides = dict(overrides)
    task_profile_id = payload_overrides.pop("profile_id", profile.profile_id)
    task = TaskRepository(db_session).create(_task(task_profile_id, **payload_overrides))
    task_ref = "task:test"
    state = State(
        query="/execute",
        task_selection={"task_ref": task_ref, "selected": True},
        object_reference_index={task_ref: str(task.task_id)},
    )

    result = prepare_execution(state, Runtime(context=_context(db_session)))

    assert result.execution_preparation is not None
    assert result.execution_preparation.error_code == error_code


def test_prepare_execution_rejects_parent_task(db_session) -> None:
    profile = DataProfileRepository(db_session).create(_profile())
    parent = TaskRepository(db_session).create(_task(profile.profile_id))
    TaskRepository(db_session).create(
        _task(profile.profile_id, parent_task_id=parent.task_id, title="Child analysis")
    )
    task_ref = "task:parent"

    result = prepare_execution(
        State(
            query="/execute",
            task_selection={"task_ref": task_ref, "selected": True},
            object_reference_index={task_ref: str(parent.task_id)},
        ),
        Runtime(context=_context(db_session)),
    )

    assert result.execution_preparation is not None
    assert result.execution_preparation.error_code == "task_has_child_tasks"


@pytest.mark.parametrize(
    "profile_overrides",
    [
        {"lifecycle_state": DataProfileLifecycleState.DRAFT},
        {"accepted_as_ground_truth": False},
    ],
)
def test_prepare_execution_rejects_unusable_profile(
    db_session,
    profile_overrides: dict[str, object],
) -> None:
    profile = DataProfileRepository(db_session).create(_profile(**profile_overrides))
    task = TaskRepository(db_session).create(_task(profile.profile_id))
    task_ref = "task:unusable-profile"

    result = prepare_execution(
        State(
            query="/execute",
            task_selection={"task_ref": task_ref, "selected": True},
            object_reference_index={task_ref: str(task.task_id)},
        ),
        Runtime(context=_context(db_session)),
    )

    assert result.execution_preparation is not None
    assert result.execution_preparation.error_code == "data_profile_not_accepted"


def test_prepare_execution_rejects_missing_profile(db_session, monkeypatch) -> None:
    task = _persist_ready_task(db_session)
    monkeypatch.setattr(
        DataProfileRepository,
        "get_by_id",
        lambda _repository, _profile_id: None,
    )
    task_ref = "task:missing-profile"

    result = prepare_execution(
        State(
            query="/execute",
            task_selection={"task_ref": task_ref, "selected": True},
            object_reference_index={task_ref: str(task.task_id)},
        ),
        Runtime(context=_context(db_session)),
    )

    assert result.execution_preparation is not None
    assert result.execution_preparation.error_code == "unknown_data_profile"


def test_prepare_execution_reuses_existing_nonterminal_hypothesis(db_session) -> None:
    task = _persist_ready_task(db_session)
    specification = task.analytical_specification
    assert specification is not None and task.profile_id is not None
    HypothesisRepository(db_session).create(
        Hypothesis(
            task_id=task.task_id,
            profile_id=task.profile_id,
            statement=specification.hypothesis_statement,
            variables=specification.variable_bindings,
            scope=specification.scope,
            validation_method=specification.validation_method,
            evidence_expectation=specification.evidence_expectation,
        )
    )
    task_ref = "task:existing-hypothesis"

    result = prepare_execution(
        State(
            query="/execute",
            task_selection={"task_ref": task_ref, "selected": True},
            object_reference_index={task_ref: str(task.task_id)},
        ),
        Runtime(context=_context(db_session)),
    )

    assert result.execution_preparation is not None
    assert result.execution_preparation.prepared
    assert result.prepared_execution is not None
    assert result.prepared_execution.hypothesis_ref is not None
    assert result.resolve_object_reference(result.prepared_execution.hypothesis_ref) == str(
        HypothesisRepository(db_session).list(task_id=task.task_id)[0].hypothesis_id
    )


def test_prepare_execution_rejects_ungrounded_specification_variable(db_session) -> None:
    profile = DataProfileRepository(db_session).create(_profile())
    specification = _task(profile.profile_id).analytical_specification
    assert specification is not None
    task = TaskRepository(db_session).create(
        _task(
            profile.profile_id,
            analytical_specification=specification.model_copy(
                update={"variable_bindings": ["unknown_metric"]}
            ),
        )
    )
    task_ref = "task:ungrounded"

    result = prepare_execution(
        State(
            query="/execute",
            task_selection={"task_ref": task_ref, "selected": True},
            object_reference_index={task_ref: str(task.task_id)},
        ),
        Runtime(context=_context(db_session)),
    )

    assert result.execution_preparation is not None
    assert result.execution_preparation.error_code == "ungrounded_variable_binding"


def test_execute_graph_persists_one_authorized_chain_without_second_approval(
    db_session,
) -> None:
    task = _persist_ready_task(db_session)
    executor = FakeExecutor()
    request_model = FailIfCalledRequestModel()
    graph = build_graph()

    final_state = State.model_validate(
        graph.invoke(
            State(
                query=f"/execute {task.task_id}",
                planner_decision={"action": "approve"},
            ),
            context=_context(db_session, executor, request_model),
        )
    )

    assert final_state.task_selection is not None and final_state.task_selection.selected
    assert final_state.execution_review is not None and final_state.execution_review.succeeded
    assert final_state.commit_result is not None
    assert final_state.commit_result.failed_operation_ids == [], final_state.commit_result.errors
    assert len(final_state.commit_result.committed_operation_ids) == 6
    assert request_model.calls == 0
    assert len(executor.requests) == 1
    request = executor.requests[0]
    assert final_state.resolve_object_reference(request.task_ref) == str(task.task_id)
    assert final_state.resolve_object_reference(request.data_profile_ref) == str(task.profile_id)
    assert request.specification.method_parameters == [MethodParameter(name="alpha", value=0.05)]
    assert request.deterministic_seed == 17
    assert "assumptions" not in type(request).model_fields
    hypothesis = HypothesisRepository(db_session).list(task_id=task.task_id)
    assert len(hypothesis) == 1
    analysis_frames = AnalysisFrameRepository(db_session).list(data_profile_id=task.profile_id)
    runs = ExecutionRunRepository(db_session).list(hypothesis_id=hypothesis[0].hypothesis_id)
    evidence = EvidenceRepository(db_session).list_for_hypothesis(hypothesis[0].hypothesis_id)
    discoveries = DiscoveryRepository(db_session).list_for_hypothesis(hypothesis[0].hypothesis_id)
    assert len(analysis_frames) == len(runs) == len(evidence) == len(discoveries) == 1
    assert evidence[0].profile_id == hypothesis[0].profile_id
    assert evidence[0].hypothesis_id == hypothesis[0].hypothesis_id
    assert discoveries[0].hypothesis_id == hypothesis[0].hypothesis_id
    assert discoveries[0].evidence_ids == [evidence[0].evidence_id]
    assert discoveries[0].validity_basis.assumptions_excluded_from_inference is True
    assert hypothesis[0].status.value == "confirmed"
    assert TaskRepository(db_session).get_by_id(task.task_id).lifecycle_state.value == "completed"
    assert SessionFrameRepository(db_session).list() == []

    repeated_state = State.model_validate(
        graph.invoke(
            State(query=f"/execute {task.task_id}"),
            context=_context(db_session, executor, request_model),
        )
    )
    assert repeated_state.execution_preparation is not None
    assert repeated_state.execution_preparation.error_code == "task_not_active"
    assert len(executor.requests) == 1
    assert len(HypothesisRepository(db_session).list(task_id=task.task_id)) == 1
    assert (
        len(DiscoveryRepository(db_session).list_for_hypothesis(hypothesis[0].hypothesis_id)) == 1
    )


def test_execute_graph_failure_keeps_task_active_and_creates_no_evidence_or_discovery(
    db_session,
) -> None:
    task = _persist_ready_task(db_session)
    executor = FakeExecutor(fail=True)
    request_model = FailIfCalledRequestModel()
    final_state = State.model_validate(
        build_graph().invoke(
            State(
                query=f"/execute {task.task_id}",
                planner_decision={"action": "approve"},
            ),
            context=_context(db_session, executor, request_model),
        )
    )

    hypothesis = HypothesisRepository(db_session).list(task_id=task.task_id)
    assert final_state.execution_review is not None
    assert final_state.execution_review.reviewed
    assert not final_state.execution_review.succeeded
    assert final_state.commit_result is not None
    assert final_state.commit_result.failed_operation_ids == [], final_state.commit_result.errors
    assert len(final_state.commit_result.committed_operation_ids) >= 1
    assert request_model.calls == 0
    assert len(executor.requests) == len(hypothesis) == 1
    assert hypothesis[0].status.value == "approved"
    assert len(AnalysisFrameRepository(db_session).list(data_profile_id=task.profile_id)) == 1
    runs = ExecutionRunRepository(db_session).list(hypothesis_id=hypothesis[0].hypothesis_id)
    assert len(runs) == 1
    assert runs[0].status == "failed"
    assert EvidenceRepository(db_session).list_for_hypothesis(hypothesis[0].hypothesis_id) == []
    assert DiscoveryRepository(db_session).list_for_hypothesis(hypothesis[0].hypothesis_id) == []
    assert TaskRepository(db_session).get_by_id(task.task_id).lifecycle_state.value == "active"
    assert SessionFrameRepository(db_session).list() == []


def test_execution_does_not_dispatch_without_an_explicit_approval(db_session) -> None:
    task = _persist_ready_task(db_session)
    executor = FakeExecutor()

    final_state = State.model_validate(
        build_graph().invoke(
            State(query=f"/execute {task.task_id}"),
            context=_context(db_session, executor, FailIfCalledRequestModel()),
        )
    )

    assert final_state.pending_interaction is not None
    assert final_state.pending_interaction.kind == "execution_approval"
    assert final_state.execution_revalidation is None
    assert executor.requests == []
    assert HypothesisRepository(db_session).list(task_id=task.task_id) == []
    assert ExecutionRunRepository(db_session).list(task_id=task.task_id) == []


def test_changed_contract_cannot_reuse_execution_approval(db_session) -> None:
    task = _persist_ready_task(db_session)
    task_ref = "task:approval-check"
    state = prepare_execution(
        State(
            query="/execute",
            task_selection={"task_ref": task_ref, "selected": True},
            object_reference_index={task_ref: str(task.task_id)},
        ),
        Runtime(context=_context(db_session)),
    )
    state = request_user_input(state, Runtime(context=_context(db_session)))
    assert state.pending_interaction is not None
    assert state.prepared_execution is not None

    state.prepared_execution.contract_fingerprint = "altered-contract"
    state.planner_decision = PlannerDecision(action="approve")
    state = process_decision(state, Runtime(context=_context(db_session)))

    assert state.execution_revalidation is not None
    assert not state.execution_revalidation.valid
    assert state.execution_revalidation.error_code == "stale_execution_approval"


def test_hypothesis_accumulates_evidence_until_explicit_finalization(db_session) -> None:
    task = _persist_ready_task(db_session)
    context = _context(db_session, FakeExecutor(finalize=False), FailIfCalledRequestModel())
    first_state = State.model_validate(
        build_graph().invoke(
            State(
                query=f"/execute {task.task_id}",
                planner_decision={"action": "approve"},
            ),
            context=context,
        )
    )
    hypothesis = HypothesisRepository(db_session).list(task_id=task.task_id)[0]
    assert first_state.hypothesis_evaluation is not None
    assert not first_state.hypothesis_evaluation.evaluated
    assert len(EvidenceRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)) == 1
    assert DiscoveryRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id) == []
    assert hypothesis.status.value == "awaiting_additional_evidence"

    second_state = State.model_validate(
        build_graph().invoke(
            State(
                query=f"/execute {task.task_id}",
                planner_decision={"action": "approve"},
            ),
            context=_context(db_session, FakeExecutor(finalize=True), FailIfCalledRequestModel()),
        )
    )
    discoveries = DiscoveryRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)
    evidence = EvidenceRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)
    assert second_state.hypothesis_evaluation is not None
    assert second_state.hypothesis_evaluation.evaluated
    assert len(evidence) == 2
    assert len(discoveries) == 1
    assert set(discoveries[0].evidence_ids) == {item.evidence_id for item in evidence}


@pytest.mark.parametrize(
    ("executor", "error_code"),
    [
        (FakeExecutor(output_method="unexpected_method"), "executor_method_mismatch"),
        (
            FakeExecutor(output_parameters=[MethodParameter(name="alpha", value=0.01)]),
            "executor_parameter_mismatch",
        ),
    ],
)
def test_review_rejects_executor_identity_drift(
    db_session,
    executor: FakeExecutor,
    error_code: str,
) -> None:
    task = _persist_ready_task(db_session)

    final_state = State.model_validate(
        build_graph().invoke(
            State(
                query=f"/execute {task.task_id}",
                planner_decision={"action": "approve"},
            ),
            context=_context(db_session, executor, FailIfCalledRequestModel()),
        )
    )

    assert final_state.execution_review is not None
    assert final_state.execution_review.error_code == error_code
    assert len(executor.requests) == 1
    assert len(HypothesisRepository(db_session).list(task_id=task.task_id)) == 1
    assert EvidenceRepository(db_session).list() == []
    assert DiscoveryRepository(db_session).list() == []
    persisted_task = TaskRepository(db_session).get_by_id(task.task_id)
    assert persisted_task is not None
    assert persisted_task.lifecycle_state == TaskLifecycleState.ACTIVE


def test_executor_result_rejects_status_or_failure_contract_drift() -> None:
    analysis_frame = AnalysisFrameObservation(frame_hash="test-frame")

    with pytest.raises(ValueError, match="status must match"):
        ExecutorResult(
            status="completed",
            analysis_frame=analysis_frame,
            execution_run=ExecutionRunObservation(status="failed"),
            evidence_observation=EvidenceObservation(
                evidence_type=EvidenceType.STATISTICAL_TEST,
                method="deterministic_test",
                result_summary=EvidenceResultSummary(summary="Observed result."),
            ),
            evaluation=HypothesisEvaluationDraft(outcome=HypothesisEvidenceOutcome.SUPPORTS),
        )

    with pytest.raises(ValueError, match="failure information"):
        ExecutorResult(
            status="failed",
            analysis_frame=analysis_frame,
            execution_run=ExecutionRunObservation(status="failed"),
        )


def test_inconclusive_execution_does_not_overclaim_no_relationship(db_session) -> None:
    task = _persist_ready_task(db_session)
    executor = FakeExecutor(outcome=HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE)

    build_graph().invoke(
        State(
            query=f"/execute {task.task_id}",
            planner_decision={"action": "approve"},
        ),
        context=_context(db_session, executor, FailIfCalledRequestModel()),
    )

    hypothesis = HypothesisRepository(db_session).list(task_id=task.task_id)[0]
    discovery = DiscoveryRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)[0]
    assert discovery.epistemic_status == DiscoveryEpistemicStatus.INSUFFICIENT_EVIDENCE
    assert "insufficient" in discovery.claim.statement.lower()
    assert "no relationship" not in discovery.claim.statement.lower()


def test_execution_bundle_rolls_back_target_records_when_one_operation_fails(
    db_session,
) -> None:
    task = _persist_ready_task(db_session)
    specification = task.analytical_specification
    assert specification is not None and task.profile_id is not None
    hypothesis = Hypothesis(
        task_id=task.task_id,
        profile_id=task.profile_id,
        statement=specification.hypothesis_statement,
        variables=specification.variable_bindings,
        scope=specification.scope,
        validation_method=specification.validation_method,
        evidence_expectation=specification.evidence_expectation,
    )
    hypothesis_operation = PlannerOperation(
        operation_type=PlannerOperationType.CREATE_HYPOTHESIS,
        payload=hypothesis.model_dump(mode="json"),
        produced_by_node=PlannerNodeName.REVIEW_EXECUTION,
        approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
    )
    invalid_frame_operation = PlannerOperation(
        operation_type=PlannerOperationType.CREATE_ANALYSIS_FRAME,
        payload=AnalysisFrame(
            data_profile_id=uuid4(),
            frame_hash="missing-profile-frame",
        ).model_dump(mode="json"),
        produced_by_node=PlannerNodeName.REVIEW_EXECUTION,
        approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
    )

    result = commit_planner_operations(
        db_session,
        [hypothesis_operation, invalid_frame_operation],
    )

    assert result.committed_operation_ids == []
    assert result.failed_operation_ids == [invalid_frame_operation.operation_id]
    assert HypothesisRepository(db_session).list(task_id=task.task_id) == []
    assert AnalysisFrameRepository(db_session).list() == []


def test_evidence_repository_rejects_orphans_and_cross_profile_evidence(db_session) -> None:
    profile = DataProfileRepository(db_session).create(_profile())
    other_profile = DataProfileRepository(db_session).create(
        _profile(dataset_path="data/other-customers.csv")
    )
    task = TaskRepository(db_session).create(_task(profile.profile_id))
    hypothesis = HypothesisRepository(db_session).create(
        Hypothesis(
            task_id=task.task_id,
            profile_id=profile.profile_id,
            statement=task.analytical_specification.hypothesis_statement,
            variables=task.analytical_specification.variable_bindings,
            scope=task.analytical_specification.scope,
            validation_method=task.analytical_specification.validation_method,
            evidence_expectation=task.analytical_specification.evidence_expectation,
        )
    )

    def evidence(hypothesis_id: UUID, profile_id: UUID) -> Evidence:
        return Evidence(
            hypothesis_id=hypothesis_id,
            profile_id=profile_id,
            analysis_frame_ref="analysis-frame:admission-test",
            execution_run_ref="execution-run:admission-test",
            evidence_type=EvidenceType.STATISTICAL_TEST,
            method="deterministic_test",
            provenance=EvidenceProvenance(
                analysis_frame_ref="analysis-frame:admission-test",
                execution_run_ref="execution-run:admission-test",
            ),
            result_summary=EvidenceResultSummary(summary="Observed test result."),
        )

    repository = EvidenceRepository(db_session)
    with pytest.raises(ValueError, match="existing Hypothesis"):
        repository.create(evidence(uuid4(), profile.profile_id))
    with pytest.raises(ValueError, match="existing DataProfile"):
        repository.create(evidence(hypothesis.hypothesis_id, uuid4()))
    with pytest.raises(ValueError, match="must match"):
        repository.create(evidence(hypothesis.hypothesis_id, other_profile.profile_id))
    assert repository.list() == []

    accepted = repository.create(evidence(hypothesis.hypothesis_id, profile.profile_id))
    assert accepted.hypothesis_id == hypothesis.hypothesis_id

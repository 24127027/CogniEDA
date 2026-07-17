from __future__ import annotations

import asyncio
from uuid import UUID, uuid4

import pytest
from langgraph.runtime import Runtime

from agents.executor import ExecutorContext, ExecutorDispatcher, ExecutorInput, ExecutorRegistry
from agents.executor.capabilities import CapabilitySpec
from agents.planner.agent import Planner
from agents.planner.graph import build_graph
from agents.planner.nodes import (
    TaskManagementDraft,
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
    RequestUnderstanding,
    RequestUnderstandingModel,
    State,
    TaskCreateDraft,
)
from application.orchestrator import reconciler as reconciliation_module
from application.orchestrator.cancellation import authorize_retry
from application.orchestrator.dispatcher import dispatch_pending_attempts
from application.orchestrator.finalizer import finalize_attempt
from application.orchestrator.planner_commit import commit_planner_operations
from application.orchestrator.receiver import submit_execution_result
from application.orchestrator.scientific_processing import _method_parameter_hash
from db.models import ExecutionOutboxRecord
from db.session import get_session
from repositories import (
    AnalysisFrameRepository,
    DataProfileRepository,
    DiscoveryRepository,
    EvidenceRepository,
    ExecutionApprovalRepository,
    ExecutionInboxRepository,
    ExecutionOutboxRepository,
    ExecutionRunRepository,
    HypothesisRepository,
    PlannerOperationRepository,
    SessionFrameRepository,
    TaskRepository,
)
from schemas.artifacts import (
    AnalyticalSpecification,
    DataProfile,
    EvaluationThresholds,
    Evidence,
    Hypothesis,
    Task,
)
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
    ExecutionRunStatus,
    HypothesisEvidenceOutcome,
    HypothesisStatus,
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
        advisory_outcome: HypothesisEvidenceOutcome | None = None,
        finalize: bool = True,
        raise_error: bool = False,
        output_executor_type: str | None = None,
        output_method: str | None = None,
        output_parameters: list[MethodParameter] | None = None,
    ) -> None:
        self.fail = fail
        self.outcome = outcome
        self.advisory_outcome = advisory_outcome
        self.finalize = finalize
        self.raise_error = raise_error
        self.output_executor_type = output_executor_type
        self.output_method = output_method
        self.output_parameters = output_parameters
        self.requests: list[ExecutorInput] = []

    async def run(self, input: ExecutorInput, context: ExecutorContext) -> ExecutorResult:
        request = input
        self.requests.append(request)
        if self.raise_error:
            raise RuntimeError("deterministic executor exception")
        analysis_frame = AnalysisFrameObservation(
            frame_hash="test-frame-v1",
            column_refs=request.specification.variable_bindings,
        )
        execution_run = ExecutionRunObservation(
            executor_type=self.output_executor_type or request.specification.executor_id,
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
                    metric_value=(
                        0.01
                        if self.outcome == HypothesisEvidenceOutcome.SUPPORTS
                        else (
                            0.1 if self.outcome == HypothesisEvidenceOutcome.INCONCLUSIVE else None
                        )
                    ),
                ),
                code_reference="tests/agents/planner/test_execution_spine.py",
            ),
            evaluation=HypothesisEvaluationDraft(
                outcome=self.advisory_outcome or self.outcome,
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


class FixedTaskManagementModel:
    """Task proposal seam used to exercise the public planner resume path."""

    def draft(self, prompt: str) -> TaskManagementDraft:
        return TaskManagementDraft(
            task_create_payloads=[
                TaskCreateDraft(
                    title="Review missing values",
                    description="Inspect missing-value patterns before execution.",
                )
            ]
        )


def _context(
    db_session,
    request_model: RequestUnderstandingModel | None = None,
) -> Context:
    return Context(
        database_url=str(db_session.get_bind().url),
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
            decision_rule=EvaluationThresholds(p_value=0.05),
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


def _dispatch_and_finalize(db_session, executor: FakeExecutor, task: Task) -> UUID:
    """Advance an admitted attempt through fresh dispatcher/finalizer sessions."""

    runs = ExecutionRunRepository(db_session).list(
        task_id=task.task_id,
        status=ExecutionRunStatus.ADMITTED,
    )
    assert len(runs) == 1
    run = runs[0]
    database_url = str(db_session.get_bind().url)
    dispatch_session = get_session(database_url)
    try:
        assert (
            asyncio.run(
                dispatch_pending_attempts(
                    dispatch_session,
                    _dispatcher_for(executor),
                    "test-worker",
                )
            )
            == 1
        )
    finally:
        dispatch_session.close()
    finalizer_session = get_session(database_url)
    try:
        assert finalize_attempt(finalizer_session, run.execution_run_id)
    finally:
        finalizer_session.close()
    return run.execution_run_id


def _dispatcher_for(executor: FakeExecutor) -> ExecutorDispatcher:
    registry = ExecutorRegistry()
    registry.register_factory(
        CapabilitySpec(id="deterministic", description="Deterministic test executor."),
        lambda: executor,
    )
    return ExecutorDispatcher(registry)


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
            context=_context(db_session, request_model),
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
            context=_context(db_session, request_model),
        )
    )

    assert final_state.task_selection is not None and final_state.task_selection.selected
    assert final_state.execution_admission is not None and final_state.execution_admission.admitted
    assert request_model.calls == 0
    assert len(executor.requests) == 0
    _dispatch_and_finalize(db_session, executor, task)
    assert len(executor.requests) == 1
    request = executor.requests[0]
    assert request.task_id == task.task_id
    assert request.data_profile_id == task.profile_id
    assert request.specification.method_parameters == [MethodParameter(name="alpha", value=0.05)]
    assert request.deterministic_seed == 17
    assert "assumptions" not in type(request).model_fields
    hypothesis = HypothesisRepository(db_session).list(task_id=task.task_id)
    assert len(hypothesis) == 1
    assert request.hypothesis_id == hypothesis[0].hypothesis_id
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
    frames = SessionFrameRepository(db_session).list()
    assert len(frames) == 1
    frame = frames[0]
    assert frame.active_data_profile_refs == [task.profile_id]
    assert frame.relevant_discovery_refs == [discoveries[0].discovery_id]
    assert frame.supporting_evidence_refs == [evidence[0].evidence_id]
    assert str(discoveries[0].discovery_id) in frame.inclusion_reasons
    assert frame.active_assumptions == []

    repeated_state = State.model_validate(
        graph.invoke(
            State(query=f"/execute {task.task_id}"),
            context=_context(db_session, request_model),
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
            context=_context(db_session, request_model),
        )
    )

    hypothesis = HypothesisRepository(db_session).list(task_id=task.task_id)
    assert final_state.execution_admission is not None and final_state.execution_admission.admitted
    assert request_model.calls == 0
    _dispatch_and_finalize(db_session, executor, task)
    assert len(executor.requests) == len(hypothesis) == 1
    hypothesis = HypothesisRepository(db_session).list(task_id=task.task_id)
    assert hypothesis[0].status.value == "approved"
    assert AnalysisFrameRepository(db_session).list(data_profile_id=task.profile_id) == []
    runs = ExecutionRunRepository(db_session).list(hypothesis_id=hypothesis[0].hypothesis_id)
    assert len(runs) == 1
    assert runs[0].status == "execution_failed"
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
            context=_context(db_session, FailIfCalledRequestModel()),
        )
    )

    assert final_state.pending_interaction is not None
    assert final_state.pending_interaction.kind == "execution_approval"
    assert final_state.execution_revalidation is None
    assert executor.requests == []
    assert HypothesisRepository(db_session).list(task_id=task.task_id) == []
    assert ExecutionRunRepository(db_session).list(task_id=task.task_id) == []


def test_public_planner_commits_only_matching_task_proposal_after_resume(db_session) -> None:
    database_url = str(db_session.get_bind().url)
    context = Context(
        session_id="task-proposal-session",
        task_management_model=FixedTaskManagementModel(),
    )

    first = asyncio.run(
        Planner(database_url=database_url).run(
            "/manage_task create a missing-value review task",
            context,
        )
    ).payload

    assert first.pending_interaction is not None
    assert first.pending_interaction.kind == "planner_operation_approval"
    assert first.committed_operation_ids == []
    assert first.pending_interaction.operation_ids
    assert TaskRepository(db_session).list() == []

    tampered = asyncio.run(
        Planner(database_url=database_url).run(
            "/approve",
            Context(session_id=context.session_id),
            decision=PlannerDecision(
                action="approve",
                proposal_id="tampered-proposal",
                selected_ids=first.pending_interaction.operation_ids,
            ),
        )
    ).payload

    assert tampered.committed_operation_ids == []
    assert tampered.commit_result is not None
    assert tampered.commit_result.skipped_operation_ids
    assert TaskRepository(db_session).list() == []

    wrong_session = asyncio.run(
        Planner(database_url=database_url).run(
            "/approve",
            Context(session_id="other-task-proposal-session"),
            decision=PlannerDecision(
                action="approve",
                proposal_id=first.pending_interaction.proposal_id,
                selected_ids=first.pending_interaction.operation_ids,
            ),
        )
    ).payload

    assert wrong_session.controlled_error is not None
    assert wrong_session.controlled_error.code == "invalid_planner_operation_proposal"
    assert TaskRepository(db_session).list() == []

    malformed = asyncio.run(
        Planner(database_url=database_url).run(
            "/approve",
            Context(session_id=context.session_id),
            decision=PlannerDecision(
                action="approve",
                proposal_id=first.pending_interaction.proposal_id,
            ),
        )
    ).payload

    assert malformed.controlled_error is not None
    assert malformed.controlled_error.code == "planner_operation_resume_unavailable"
    assert TaskRepository(db_session).list() == []

    second = asyncio.run(
        Planner(database_url=database_url).run(
            "/approve",
            Context(session_id=context.session_id),
            decision=PlannerDecision(
                action="approve",
                proposal_id=first.pending_interaction.proposal_id,
                selected_ids=first.pending_interaction.operation_ids,
            ),
        )
    ).payload

    assert second.commit_result is not None
    assert second.commit_result.succeeded
    assert second.committed_operation_ids == second.commit_result.committed_operation_ids
    assert len(TaskRepository(db_session).list()) == 1

    replay = asyncio.run(
        Planner(database_url=database_url).run(
            "/approve",
            Context(session_id=context.session_id),
            decision=PlannerDecision(
                action="approve",
                proposal_id=first.pending_interaction.proposal_id,
                selected_ids=first.pending_interaction.operation_ids,
            ),
        )
    ).payload

    assert replay.controlled_error is not None
    assert replay.controlled_error.code == "invalid_planner_operation_proposal"
    assert len(TaskRepository(db_session).list()) == 1


def test_public_planner_resumes_durable_approval_in_a_new_instance(db_session, monkeypatch) -> None:
    task = _persist_ready_task(db_session)
    database_url = str(db_session.get_bind().url)
    executor = FakeExecutor()
    context = Context(session_id="restart-safe-session")
    reconcile_calls = []
    original_reconcile = reconciliation_module.reconcile_execution_attempts

    def track_reconciliation(session) -> None:
        reconcile_calls.append(session)
        original_reconcile(session)

    monkeypatch.setattr(
        reconciliation_module,
        "reconcile_execution_attempts",
        track_reconciliation,
    )

    first = asyncio.run(
        Planner(database_url=database_url).run(
            f"/execute {task.task_id}",
            context,
        )
    ).payload

    assert first.pending_interaction is not None
    assert first.pending_interaction.proposal_id is not None
    assert executor.requests == []
    approval = ExecutionApprovalRepository(db_session).get_by_id(
        UUID(first.pending_interaction.proposal_id)
    )
    assert approval is not None
    assert approval.session_id == context.session_id
    assert approval.task_id == task.task_id
    assert approval.contract_fingerprint == first.pending_interaction.snapshot_hash

    second = asyncio.run(
        Planner(database_url=database_url).run(
            "/approve",
            context,
            decision=PlannerDecision(
                action="approve",
                proposal_id=first.pending_interaction.proposal_id,
                execution_ref=first.pending_interaction.payload["execution_ref"],
            ),
        )
    ).payload

    assert second.controlled_error is None
    assert second.executor_dispatch_ref is not None
    assert len(executor.requests) == 0
    _dispatch_and_finalize(db_session, executor, task)
    assert len(executor.requests) == 1
    hypothesis = HypothesisRepository(db_session).list(task_id=task.task_id)
    assert len(hypothesis) == 1
    discoveries = DiscoveryRepository(db_session).list_for_hypothesis(hypothesis[0].hypothesis_id)
    assert len(discoveries) == 1
    assert len(reconcile_calls) == 2


def test_planner_context_has_no_retired_executor_dependency() -> None:
    assert "analytical_executor" not in Context.model_fields
    assert "analytical_executor" not in Planner.__init__.__annotations__


def test_durable_topology_survives_planner_and_dispatcher_replacement(db_session) -> None:
    """Admission, dispatch, receipt, and finalization share only database state."""

    task = _persist_ready_task(db_session)
    database_url = str(db_session.get_bind().url)
    planner_executor = FakeExecutor()
    context = Context(session_id="durable-topology")
    first = asyncio.run(
        Planner(database_url=database_url).run(f"/execute {task.task_id}", context)
    ).payload
    assert first.pending_interaction is not None
    assert planner_executor.requests == []

    admitted = asyncio.run(
        Planner(database_url=database_url).run(
            "/approve",
            context,
            decision=PlannerDecision(
                action="approve",
                proposal_id=first.pending_interaction.proposal_id,
                execution_ref=first.pending_interaction.payload["execution_ref"],
            ),
        )
    ).payload
    assert admitted.executor_dispatch_ref is not None
    assert planner_executor.requests == []
    run_id = UUID(admitted.executor_dispatch_ref)
    assert len(ExecutionOutboxRepository(db_session).list(execution_run_id=run_id)) == 1
    assert (
        EvidenceRepository(db_session).list_for_hypothesis(
            HypothesisRepository(db_session).list(task_id=task.task_id)[0].hypothesis_id
        )
        == []
    )

    dispatcher_executor = FakeExecutor()
    dispatch_session = get_session(database_url)
    try:
        assert (
            asyncio.run(
                dispatch_pending_attempts(
                    dispatch_session,
                    _dispatcher_for(dispatcher_executor),
                    "worker-b",
                )
            )
            == 1
        )
    finally:
        dispatch_session.close()
    assert len(dispatcher_executor.requests) == 1
    assert dispatcher_executor.requests[0].execution_run_id == run_id
    assert len(ExecutionInboxRepository(db_session).list(execution_run_id=run_id)) == 1

    finalizer_session = get_session(database_url)
    try:
        assert finalize_attempt(finalizer_session, run_id) is True
        assert finalize_attempt(finalizer_session, run_id) is True
    finally:
        finalizer_session.close()
    hypothesis = HypothesisRepository(db_session).list(task_id=task.task_id)[0]
    assert len(EvidenceRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)) == 1
    assert len(DiscoveryRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)) == 1


def test_malformed_durable_payload_fails_without_invoking_executor(db_session) -> None:
    task = _persist_ready_task(db_session)
    state = State.model_validate(
        build_graph().invoke(
            State(query=f"/execute {task.task_id}", planner_decision={"action": "approve"}),
            context=_context(db_session, FailIfCalledRequestModel()),
        )
    )
    assert state.execution_admission is not None
    assert state.execution_admission.execution_run_ref is not None
    run_id = UUID(state.resolve_object_reference(state.execution_admission.execution_run_ref))
    outbox = ExecutionOutboxRepository(db_session).list(execution_run_id=run_id)[0]
    record = db_session.get(ExecutionOutboxRecord, outbox.outbox_id)
    assert record is not None
    record.prepared_payload = {}
    db_session.add(record)
    db_session.commit()

    executor = FakeExecutor()
    dispatch_session = get_session(str(db_session.get_bind().url))
    try:
        assert (
            asyncio.run(
                dispatch_pending_attempts(
                    dispatch_session,
                    _dispatcher_for(executor),
                    "malformed-worker",
                )
            )
            == 1
        )
    finally:
        dispatch_session.close()

    assert executor.requests == []
    inbox = ExecutionInboxRepository(db_session).list(execution_run_id=run_id)
    assert len(inbox) == 1
    assert inbox[0].executor_status == "failed"
    finalizer_session = get_session(str(db_session.get_bind().url))
    try:
        assert finalize_attempt(finalizer_session, run_id) is True
    finally:
        finalizer_session.close()
    failed_run = ExecutionRunRepository(db_session).get_by_id(run_id)
    assert failed_run is not None and failed_run.status == "execution_failed"


@pytest.mark.parametrize("failure_mode", ["unknown", "factory", "executor"])
def test_dispatch_resolution_and_executor_failures_reach_inbox(
    db_session,
    failure_mode: str,
) -> None:
    task = _persist_ready_task(db_session)
    state = State.model_validate(
        build_graph().invoke(
            State(query=f"/execute {task.task_id}", planner_decision={"action": "approve"}),
            context=_context(db_session, FailIfCalledRequestModel()),
        )
    )
    assert state.execution_admission is not None
    assert state.execution_admission.execution_run_ref is not None
    run_id = UUID(state.resolve_object_reference(state.execution_admission.execution_run_ref))

    executor = FakeExecutor(raise_error=failure_mode == "executor")
    registry = ExecutorRegistry()
    if failure_mode == "factory":

        def failing_factory():
            raise RuntimeError("deterministic factory exception")

        registry.register_factory(
            CapabilitySpec(id="deterministic", description="Failing test factory."),
            failing_factory,
        )
    elif failure_mode == "executor":
        registry.register_factory(
            CapabilitySpec(id="deterministic", description="Failing test executor."),
            lambda: executor,
        )

    dispatch_session = get_session(str(db_session.get_bind().url))
    try:
        assert (
            asyncio.run(
                dispatch_pending_attempts(
                    dispatch_session,
                    ExecutorDispatcher(registry),
                    f"{failure_mode}-worker",
                )
            )
            == 1
        )
    finally:
        dispatch_session.close()

    inbox = ExecutionInboxRepository(db_session).list(execution_run_id=run_id)
    assert len(inbox) == 1
    assert inbox[0].executor_status == "failed"
    assert inbox[0].error_message is not None
    assert len(executor.requests) == (1 if failure_mode == "executor" else 0)


def test_retry_reuses_contract_and_canonical_adapter_with_new_attempt(db_session) -> None:
    task = _persist_ready_task(db_session)
    state = State.model_validate(
        build_graph().invoke(
            State(query=f"/execute {task.task_id}", planner_decision={"action": "approve"}),
            context=_context(db_session, FailIfCalledRequestModel()),
        )
    )
    assert state.execution_admission is not None
    assert state.execution_admission.execution_run_ref is not None
    predecessor_id = UUID(
        state.resolve_object_reference(state.execution_admission.execution_run_ref)
    )
    failed_executor = FakeExecutor(fail=True)
    assert _dispatch_and_finalize(db_session, failed_executor, task) == predecessor_id

    successor_id = authorize_retry(db_session, predecessor_id, retry_reason="technical_retry")
    assert successor_id is not None
    successor = ExecutionRunRepository(db_session).get_by_id(successor_id)
    assert successor is not None
    assert successor.execution_run_id != predecessor_id
    assert successor.previous_attempt_id == predecessor_id
    assert successor.hypothesis_id == failed_executor.requests[0].hypothesis_id

    predecessor = ExecutionRunRepository(db_session).get_by_id(predecessor_id)
    assert predecessor is not None
    assert predecessor.dispatch_idempotency_key is not None
    assert predecessor.method_id is not None
    assert (
        submit_execution_result(
            db_session,
            execution_run_id=predecessor_id,
            dispatch_idempotency_key=predecessor.dispatch_idempotency_key,
            lease_epoch=predecessor.lease_epoch,
            worker_id="test-worker",
            method_id=predecessor.method_id,
            executor_status="failed",
            result=None,
            error_msg="late predecessor result",
        )
        is None
    )

    successful_executor = FakeExecutor()
    assert (
        _dispatch_and_finalize(db_session, successful_executor, task) == successor.execution_run_id
    )
    first_input = failed_executor.requests[0]
    retry_input = successful_executor.requests[0]
    assert retry_input.execution_run_id != first_input.execution_run_id
    assert retry_input.task_id == first_input.task_id
    assert retry_input.hypothesis_id == first_input.hypothesis_id
    assert retry_input.data_profile_id == first_input.data_profile_id
    assert retry_input.hypothesis == first_input.hypothesis
    assert retry_input.specification == first_input.specification

    hypothesis = HypothesisRepository(db_session).get_by_id(retry_input.hypothesis_id)
    assert hypothesis is not None
    assert len(EvidenceRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)) == 1
    assert len(DiscoveryRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)) == 1


def test_public_planner_rejects_stale_durable_approval(db_session) -> None:
    task = _persist_ready_task(db_session)
    database_url = str(db_session.get_bind().url)
    executor = FakeExecutor()
    context = Context(session_id="stale-approval-session")
    first = asyncio.run(
        Planner(database_url=database_url).run(f"/execute {task.task_id}", context)
    ).payload
    assert first.pending_interaction is not None

    from db.models import TaskRecord

    record = db_session.get(TaskRecord, task.task_id)
    assert record is not None
    record.lifecycle_state = TaskLifecycleState.PAUSED
    db_session.add(record)
    db_session.commit()

    second = asyncio.run(
        Planner(database_url=database_url).run(
            "/approve",
            context,
            decision=PlannerDecision(
                action="approve",
                proposal_id=first.pending_interaction.proposal_id,
                execution_ref=first.pending_interaction.payload["execution_ref"],
            ),
        )
    ).payload

    assert second.controlled_error is not None
    assert second.controlled_error.code == "stale_execution_approval"
    assert executor.requests == []
    assert HypothesisRepository(db_session).list(task_id=task.task_id) == []


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
    executor = FakeExecutor(finalize=False)
    context = _context(db_session, FailIfCalledRequestModel())
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
    assert first_state.execution_admission is not None and first_state.execution_admission.admitted
    _dispatch_and_finalize(db_session, executor, task)
    hypothesis = HypothesisRepository(db_session).list(task_id=task.task_id)[0]
    assert len(EvidenceRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)) == 1
    assert DiscoveryRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id) == []
    assert hypothesis.status.value == "awaiting_additional_evidence"

    second_state = State.model_validate(
        build_graph().invoke(
            State(
                query=f"/execute {task.task_id}",
                planner_decision={"action": "approve"},
            ),
            context=_context(db_session, FailIfCalledRequestModel()),
        )
    )
    discoveries = DiscoveryRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)
    evidence = EvidenceRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)
    assert (
        second_state.execution_admission is not None and second_state.execution_admission.admitted
    )
    _dispatch_and_finalize(db_session, FakeExecutor(finalize=True), task)
    discoveries = DiscoveryRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)
    evidence = EvidenceRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)
    assert len(evidence) == 2
    assert len(discoveries) == 1
    assert set(discoveries[0].evidence_ids) == {item.evidence_id for item in evidence}


@pytest.mark.parametrize(
    ("executor", "error_code"),
    [
        (FakeExecutor(output_method="unexpected_method"), "executor_method_mismatch"),
        (FakeExecutor(output_executor_type="unexpected_executor"), "executor_type_mismatch"),
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
            context=_context(db_session, FailIfCalledRequestModel()),
        )
    )

    assert final_state.execution_admission is not None and final_state.execution_admission.admitted
    _dispatch_and_finalize(db_session, executor, task)
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

    final_state = State.model_validate(
        build_graph().invoke(
            State(
                query=f"/execute {task.task_id}",
                planner_decision={"action": "approve"},
            ),
            context=_context(db_session, FailIfCalledRequestModel()),
        )
    )
    assert final_state.execution_admission is not None and final_state.execution_admission.admitted
    _dispatch_and_finalize(db_session, executor, task)

    hypothesis = HypothesisRepository(db_session).list(task_id=task.task_id)[0]
    discovery = DiscoveryRepository(db_session).list_for_hypothesis(hypothesis.hypothesis_id)[0]
    assert discovery.epistemic_status == DiscoveryEpistemicStatus.INSUFFICIENT_EVIDENCE
    assert "insufficient" in discovery.claim.statement.lower()
    assert "no relationship" not in discovery.claim.statement.lower()


def test_executor_advisory_outcome_cannot_override_deterministic_evaluation(db_session) -> None:
    task = _persist_ready_task(db_session)
    executor = FakeExecutor(advisory_outcome=HypothesisEvidenceOutcome.CONTRADICTS)

    final_state = State.model_validate(
        build_graph().invoke(
            State(
                query=f"/execute {task.task_id}",
                planner_decision={"action": "approve"},
            ),
            context=_context(db_session, FailIfCalledRequestModel()),
        )
    )

    assert final_state.execution_admission is not None and final_state.execution_admission.admitted
    _dispatch_and_finalize(db_session, executor, task)
    hypothesis = HypothesisRepository(db_session).list(task_id=task.task_id)
    assert len(hypothesis) == 1
    assert hypothesis[0].status == HypothesisStatus.APPROVED
    assert EvidenceRepository(db_session).list_for_hypothesis(hypothesis[0].hypothesis_id) == []
    assert DiscoveryRepository(db_session).list_for_hypothesis(hypothesis[0].hypothesis_id) == []


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

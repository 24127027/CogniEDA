"""Step 10 boundary characterization.

This module proves the genuine end-to-end lineage without bypassing production
governance. It exercises both upstream surfaces (root motivation authoring and
execution-ready analytical contract decomposition) and the entire durable
execution and finalization lower half.
"""

from __future__ import annotations

import ast
import asyncio
import json
import re
from uuid import UUID

from agents.executor import ExecutorContext, ExecutorDispatcher, ExecutorInput, ExecutorRegistry
from agents.executor.capabilities import CapabilitySpec
from agents.planner.agent import Planner
from agents.planner.nodes import ObjectiveManagementDraft, TaskManagementDraft
from agents.planner.types import (
    ChildTaskProposalDraft,
    Context,
    ObjectiveCreateDraft,
    PlannerDecision,
    TaskCreateDraft,
    TaskDecompositionDraft,
)
from application.orchestrator.cancellation import authorize_retry
from application.orchestrator.dispatcher import dispatch_pending_attempts
from application.orchestrator.execution_contracts import (
    AnalysisFrameObservation,
    EvidenceObservation,
    ExecutionRunObservation,
    ExecutorResult,
    HypothesisEvaluationDraft,
)
from application.orchestrator.finalizer import finalize_attempt
from application.orchestrator.receiver import submit_execution_result
from application.orchestrator.review_propagation import propagate_discovery_review
from application.orchestrator.scientific_processing import _method_parameter_hash
from db.session import get_session
from memory.retrieval_engine import DiscoveryRetrievalEngine
from memory.session_frame import SessionFrameBuilder
from repositories import (
    AssumptionRepository,
    DataProfileRepository,
    DiscoveryRepository,
    EvidenceRepository,
    ExecutionOutboxRepository,
    ExecutionRunRepository,
    HypothesisRepository,
    ObjectiveRepository,
    SessionFrameRepository,
    TaskRepository,
)
from repositories.hypothesis_repository import HypothesisUpdate
from repositories.task_repository import TaskUpdate
from schemas.artifacts import (
    AnalyticalSpecification,
    Assumption,
    DataProfile,
    Discovery,
    Evidence,
    Hypothesis,
    Task,
)
from schemas.common import (
    BaselineSummary,
    DiscoveryClaim,
    EvaluationThresholds,
    EvidenceProvenance,
    EvidenceResultSummary,
    MethodParameter,
    SchemaSummary,
    ValidityBasis,
)
from schemas.enums import (
    DataProfileLifecycleState,
    DataProfileMethod,
    DiscoveryEpistemicStatus,
    DiscoveryLifecycleState,
    EvidenceType,
    ExecutionRunStatus,
    HypothesisEvidenceOutcome,
    HypothesisStatus,
    TaskKind,
    TaskLifecycleState,
)
from schemas.retrieval import RetrievalRequest


class CreateObjectiveModel:
    def draft(self, _prompt: str) -> ObjectiveManagementDraft:
        return ObjectiveManagementDraft(
            objective_create_payloads=[
                ObjectiveCreateDraft(
                    title="Step 10 Objective",
                    statement="Prove governed lineage without epistemic leakage.",
                )
            ]
        )


class CreateRootTaskModel:
    """Allowed structured-output seam selecting only bounded local references."""

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def draft(self, prompt: str) -> TaskManagementDraft:
        self.prompts.append(prompt)
        candidate_match = re.search(
            r"Motivation candidate local references: (\[[^\n]*\])",
            prompt,
        )
        explanation_match = re.search(
            r"Candidate explanations: (\{.*\})\nRetrieval warnings:",
            prompt,
        )
        candidates = list(ast.literal_eval(candidate_match.group(1))) if candidate_match else []
        explanations = json.loads(explanation_match.group(1)) if explanation_match else {}
        references = {
            item["claim"]: reference
            for reference, item in explanations.items()
            if reference in candidates
        }
        return TaskManagementDraft(
            task_create_payloads=[
                TaskCreateDraft(
                    title="T0",
                    description="Root task testing governed motivation.",
                    task_kind=TaskKind.ORGANIZING,
                    selected_motivating_discovery_refs=[
                        references["Bootstrap claim D1"],
                        references["Bootstrap claim D2"],
                    ],
                )
            ]
        )


class RawUuidRootTaskModel:
    def __init__(self, discovery_id: UUID) -> None:
        self.discovery_id = discovery_id

    def draft(self, _prompt: str) -> TaskManagementDraft:
        return TaskManagementDraft(
            task_create_payloads=[
                TaskCreateDraft(
                    title="Unsafe T0",
                    description="Attempt a raw UUID bypass.",
                    task_kind=TaskKind.ORGANIZING,
                    selected_motivating_discovery_refs=[str(self.discovery_id)],
                )
            ]
        )


class ContextOnlyRootTaskModel:
    def draft(self, prompt: str) -> TaskManagementDraft:
        context_match = re.search(
            r"Other relevant context-only Discovery references: (\[[^\n]*\])",
            prompt,
        )
        contextual = list(ast.literal_eval(context_match.group(1))) if context_match else []
        return TaskManagementDraft(
            task_create_payloads=[
                TaskCreateDraft(
                    title="Unsafe contextual T0",
                    description="Attempt a contextual-only selection.",
                    task_kind=TaskKind.ORGANIZING,
                    selected_motivating_discovery_refs=[contextual[0]],
                )
            ]
        )


class FirstCandidateRootTaskModel:
    def draft(self, prompt: str) -> TaskManagementDraft:
        candidate_match = re.search(
            r"Motivation candidate local references: (\[[^\n]*\])",
            prompt,
        )
        candidates = list(ast.literal_eval(candidate_match.group(1))) if candidate_match else []
        return TaskManagementDraft(
            task_create_payloads=[
                TaskCreateDraft(
                    title="Stale T0",
                    description="Exercise commit-time motivation revalidation.",
                    task_kind=TaskKind.ORGANIZING,
                    selected_motivating_discovery_refs=[candidates[0]],
                )
            ]
        )


class ThreeChildDecompositionModel:
    """Allowed structured-output seam; it receives local refs, never UUIDs."""

    def __init__(self) -> None:
        self.prompts: list[str] = []
        self.error: str | None = None

    def draft(self, prompt: str) -> TaskDecompositionDraft:
        self.prompts.append(prompt)
        try:
            parent_match = re.search(r"Parent local reference: (task:[^\n]+)", prompt)
            if parent_match is None:
                raise ValueError("Missing parent local reference")
            motivation_match = re.search(
                r"Parent direct-motivation candidates: (\[[^\n]*\])",
                prompt,
            )
            motivation_refs = (
                list(ast.literal_eval(motivation_match.group(1)))
                if motivation_match is not None
                else []
            )
            explanation_match = re.search(
                r"Candidate explanations: (\{.*\})\nRetrieval warnings:",
                prompt,
            )
            explanations = (
                json.loads(explanation_match.group(1))
                if explanation_match is not None
                else {}
            )
            discovery_refs = {
                item["claim"]: reference
                for reference, item in explanations.items()
                if reference in motivation_refs
            }
            if not {"Bootstrap claim D1", "Bootstrap claim D2"} <= discovery_refs.keys():
                raise ValueError("Expected two bounded parent motivations")
            
            active_profile_match = re.search(r"data_profile_ref \(use ([^\)]+)\)", prompt)
            active_profile_ref = active_profile_match.group(1) if active_profile_match else None
            if active_profile_ref is None:
                raise ValueError("Missing active_profile_ref in prompt")

            parent_ref = parent_match.group(1)
            d1_ref = discovery_refs["Bootstrap claim D1"]
            d2_ref = discovery_refs["Bootstrap claim D2"]
            
            return TaskDecompositionDraft(
                parent_task_ref=parent_ref,
                child_task_proposals=[
                    ChildTaskProposalDraft(
                        title="T1",
                        description="Review D1.",
                        scope="review",
                        parent_task_ref=parent_ref,
                        motivated_by_discovery_refs=[d1_ref],
                        decomposition_rationale="D1-specific review.",
                        readiness_status="operational",
                        readiness_reason="Review-only child.",
                    ),
                    ChildTaskProposalDraft(
                        title="T2",
                        description="Review D2.",
                        scope="review",
                        parent_task_ref=parent_ref,
                        motivated_by_discovery_refs=[d2_ref],
                        decomposition_rationale="D2-specific review.",
                        readiness_status="operational",
                        readiness_reason="Review-only child.",
                    ),
                    ChildTaskProposalDraft(
                        title="T3",
                        description="Test the joint analytical question.",
                        scope="accepted profile",
                        parent_task_ref=parent_ref,
                        motivated_by_discovery_refs=[d1_ref, d2_ref],
                        decomposition_rationale="Joint D1/D2 analytical follow-up.",
                        readiness_status="ready_analytical",
                        data_profile_ref=active_profile_ref,
                        variables=["monthly_spend", "churned"],
                        evidence_expectation="A deterministic p-value.",
                        hypothesis_statement="Monthly spend is associated with churn.",
                        claim_type="association",
                        decision_rule=EvaluationThresholds(p_value=0.05),
                        validation_method="deterministic_test",
                        executor_id="deterministic",
                        method_parameters=[MethodParameter(name="alpha", value=0.05)],
                        deterministic_seed=17,
                    ),
                ],
            )
        except Exception as exc:
            self.error = repr(exc)
            raise


class DeterministicExecutor:
    """Allowed domain-executor seam returning observations, never FCO rows."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.requests: list[ExecutorInput] = []
        self.results: list[ExecutorResult] = []

    async def run(self, input: ExecutorInput, context: ExecutorContext) -> ExecutorResult:
        self.requests.append(input)
        analysis_frame = AnalysisFrameObservation(
            frame_hash=f"frame-{input.execution_run_id}",
            column_refs=input.specification.variable_bindings,
        )
        execution_run = ExecutionRunObservation(
            executor_type=input.specification.executor_id,
            method_id=input.specification.validation_method,
            parameter_hash=_method_parameter_hash(input.specification.method_parameters),
            status="failed" if self.fail else "completed",
        )
        if self.fail:
            result = ExecutorResult(
                status="failed",
                analysis_frame=analysis_frame,
                execution_run=execution_run,
                error_message="Deterministic technical failure.",
            )
        else:
            result = ExecutorResult(
                status="completed",
                analysis_frame=analysis_frame,
                execution_run=execution_run,
                evidence_observation=EvidenceObservation(
                    evidence_type=EvidenceType.STATISTICAL_TEST,
                    method=input.specification.validation_method,
                    parameters=input.specification.method_parameters,
                    result_summary=EvidenceResultSummary(
                        summary="Observed a deterministic p-value.",
                        key_findings=["p_value=0.01"],
                        metric_name="p_value",
                        metric_value=0.01,
                    ),
                    code_reference="tests/e2e/test_research_lineage.py",
                ),
                evaluation=HypothesisEvaluationDraft(
                    outcome=HypothesisEvidenceOutcome.SUPPORTS,
                    finalize=True,
                ),
            )
        self.results.append(result)
        return result


def _database_url(db_session) -> str:
    return str(db_session.get_bind().url)


def _run_planner(
    database_url: str,
    query: str,
    context: Context,
    decision: PlannerDecision | None = None,
):
    return asyncio.run(
        Planner(database_url=database_url).run(query, context, decision=decision)
    ).payload


def _approve_operation_batch(database_url: str, session_id: str, interaction):
    return _run_planner(
        database_url,
        "/approve",
        Context(session_id=session_id),
        PlannerDecision(
            action="approve",
            proposal_id=interaction.proposal_id,
            selected_ids=interaction.operation_ids,
        ),
    )


def _create_objective_through_public_approval(db_session, session_id: str):
    database_url = _database_url(db_session)
    proposal = _run_planner(
        database_url,
        "/objective create a governed research intent",
        Context(session_id=session_id, objective_management_model=CreateObjectiveModel()),
    )
    assert proposal.pending_interaction is not None
    assert ObjectiveRepository(db_session).get_active() is None
    approved = _approve_operation_batch(database_url, session_id, proposal.pending_interaction)
    assert approved.commit_result is not None and approved.commit_result.succeeded
    db_session.expire_all()
    objective = ObjectiveRepository(db_session).get_active()
    assert objective is not None
    return objective


def _profile() -> DataProfile:
    return DataProfile(
        dataset_path="data/customers.csv",
        method=DataProfileMethod.BASELINE_SUMMARY,
        schema_summary=SchemaSummary(column_order=["monthly_spend", "churned"]),
        baseline_summary=BaselineSummary(column_names=["monthly_spend", "churned"]),
        row_count=10,
        column_count=2,
        lifecycle_state=DataProfileLifecycleState.ACTIVE,
        accepted_as_ground_truth=True,
    )


def _analytical_specification(profile_id: UUID) -> AnalyticalSpecification:
    return AnalyticalSpecification(
        hypothesis_statement="Monthly spend is associated with churn.",
        claim_type="association",
        data_profile_id=profile_id,
        variable_bindings=["monthly_spend", "churned"],
        scope="customers in the accepted DataProfile",
        evidence_expectation="A deterministic p-value.",
        decision_rule=EvaluationThresholds(p_value=0.05),
        validation_method="deterministic_test",
        executor_id="deterministic",
        method_parameters=[MethodParameter(name="alpha", value=0.05)],
        deterministic_seed=17,
    )


def _bootstrap_discovery(
    db_session,
    profile: DataProfile,
    number: int,
) -> tuple[Discovery, Evidence]:
    """Create an explicit seed precondition through repository admission guards."""

    task_repository = TaskRepository(db_session)
    hypothesis_repository = HypothesisRepository(db_session)
    task = task_repository.create(
        Task(
            title=f"Bootstrap Task {number}",
            description="Seed-only analytical precondition.",
            task_kind=TaskKind.ANALYTICAL,
            profile_id=profile.profile_id,
            variables=["monthly_spend", "churned"],
            evidence_expectation="A valid bootstrap observation.",
            analytical_specification=_analytical_specification(profile.profile_id),
        )
    )
    hypothesis = hypothesis_repository.create(
        Hypothesis(
            task_id=task.task_id,
            profile_id=profile.profile_id,
            statement=f"Bootstrap hypothesis {number}",
            variables=["monthly_spend", "churned"],
            scope="customers in the accepted DataProfile",
            validation_method="deterministic_test",
            evidence_expectation="A valid bootstrap observation.",
            status=HypothesisStatus.TESTING,
        )
    )
    evidence = EvidenceRepository(db_session).create(
        Evidence(
            hypothesis_id=hypothesis.hypothesis_id,
            profile_id=profile.profile_id,
            analysis_frame_ref=f"bootstrap-frame-{number}",
            execution_run_ref=f"bootstrap-run-{number}",
            evidence_type=EvidenceType.STATISTICAL_TEST,
            method="deterministic_test",
            parameters=[MethodParameter(name="alpha", value=0.05)],
            provenance=EvidenceProvenance(
                analysis_frame_ref=f"bootstrap-frame-{number}",
                execution_run_ref=f"bootstrap-run-{number}",
            ),
            result_summary=EvidenceResultSummary(
                summary=f"Bootstrap observation {number}.",
                metric_name="p_value",
                metric_value=0.01,
            ),
        )
    )
    discovery = DiscoveryRepository(db_session).create(
        Discovery(
            hypothesis_id=hypothesis.hypothesis_id,
            epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
            claim=DiscoveryClaim(
                statement=f"Bootstrap claim D{number}",
                scope="customers in the accepted DataProfile",
            ),
            scope="customers in the accepted DataProfile",
            validity_basis=ValidityBasis(
                data_profile_id=profile.profile_id,
                analysis_frame_refs=[evidence.analysis_frame_ref],
                hypothesis_id=hypothesis.hypothesis_id,
                evidence_ids=[evidence.evidence_id],
                method=evidence.method,
                decision_rule=EvaluationThresholds(p_value=0.05),
            ),
            evidence_ids=[evidence.evidence_id],
        )
    )
    hypothesis_repository.update(
        hypothesis.hypothesis_id,
        HypothesisUpdate(status=HypothesisStatus.CONFIRMED),
    )
    task_repository.update(
        task.task_id,
        TaskUpdate(lifecycle_state=TaskLifecycleState.COMPLETED),
    )
    return discovery, evidence


def _dispatcher_for(executor: DeterministicExecutor) -> ExecutorDispatcher:
    registry = ExecutorRegistry()
    registry.register_factory(
        CapabilitySpec(id="deterministic", description="Deterministic test seam."),
        lambda: executor,
    )
    return ExecutorDispatcher(registry)


def test_genuine_end_to_end_research_lineage(db_session) -> None:
    """Proves the genuine end-to-end lineage without bypassing production governance."""

    database_url = _database_url(db_session)
    objective = _create_objective_through_public_approval(db_session, "step10-e2e-objective")
    profile = DataProfileRepository(db_session).create(_profile())
    d1, e1 = _bootstrap_discovery(db_session, profile, 1)
    d2, e2 = _bootstrap_discovery(db_session, profile, 2)
    assumption = AssumptionRepository(db_session).create(
        Assumption(
            statement="Unsupported planning assumption A1.",
            scope="planning only",
            source="user",
        )
    )

    # We explicitly place d1 and d2 in the SessionFrame to allow the model to use their refs
    root_frame = SessionFrameRepository(db_session).create(
        SessionFrameBuilder().build(
            objective=objective,
            data_profiles=[profile],
            assumptions=[assumption],
            discoveries=[d1, d2],
            evidence=[e1, e2],
        )
    )
    
    # 1. Author T0 with governed explicit Discovery motivation via /manage_task
    session_id = "step10-e2e-t0"
    root_task_model = CreateRootTaskModel()
    proposal_t0 = _run_planner(
        database_url,
        "/manage_task create root task",
        Context(
            session_id=session_id,
            session_frame_id=root_frame.session_frame_id,
            task_management_model=root_task_model
        ),
    )
    assert proposal_t0.pending_interaction is not None, proposal_t0.controlled_error
    wrong_session = _approve_operation_batch(
        database_url,
        "step10-e2e-wrong-session",
        proposal_t0.pending_interaction,
    )
    assert wrong_session.committed_operation_ids == []
    reordered = _run_planner(
        database_url,
        "/approve",
        Context(session_id=session_id),
        PlannerDecision(
            action="approve",
            proposal_id=proposal_t0.pending_interaction.proposal_id,
            selected_ids=list(reversed(proposal_t0.pending_interaction.operation_ids)),
        ),
    )
    assert reordered.committed_operation_ids == []
    approved_t0 = _approve_operation_batch(
        database_url,
        session_id,
        proposal_t0.pending_interaction,
    )
    assert approved_t0.commit_result is not None and approved_t0.commit_result.succeeded
    assert approved_t0.session_frame_id is not None
    assert root_task_model.prompts
    assert str(d1.discovery_id) not in root_task_model.prompts[0]
    assert str(d2.discovery_id) not in root_task_model.prompts[0]
    
    db_session.expire_all()
    tasks = TaskRepository(db_session).list()
    # 2 are bootstrap, 1 is the new T0
    assert len(tasks) == 3
    t0 = next(t for t in tasks if t.title == "T0")
    assert set(t0.motivated_by_discovery_ids) == {d1.discovery_id, d2.discovery_id}
    root_successor = SessionFrameRepository(db_session).get_by_id(approved_t0.session_frame_id)
    assert root_successor is not None
    assert t0.task_id in root_successor.active_task_refs
    replayed_t0 = _approve_operation_batch(
        database_url,
        session_id,
        proposal_t0.pending_interaction,
    )
    assert replayed_t0.committed_operation_ids == []
    assert len([task for task in TaskRepository(db_session).list() if task.title == "T0"]) == 1

    # 2. Decompose T0 to T1, T2, T3 with full analytical contract using /decompose
    session_id_decomp = "step10-e2e-decomposition"
    decomposition_model = ThreeChildDecompositionModel()
    proposal_decomp = _run_planner(
        database_url,
        f"/decompose {t0.task_id}",
        Context(
            session_id=session_id_decomp,
            session_frame_id=root_successor.session_frame_id,
            task_decomposition_model=decomposition_model,
        ),
    )
    assert proposal_decomp.pending_interaction is not None, decomposition_model.error
    approved_decomp = _approve_operation_batch(
        database_url,
        session_id_decomp,
        proposal_decomp.pending_interaction,
    )
    assert approved_decomp.commit_result is not None and approved_decomp.commit_result.succeeded
    
    db_session.expire_all()
    children = TaskRepository(db_session).list(parent_task_id=t0.task_id)
    assert {child.title for child in children} == {"T1", "T2", "T3"}
    t3 = next(child for child in children if child.title == "T3")
    t1 = next(child for child in children if child.title == "T1")
    t2 = next(child for child in children if child.title == "T2")
    assert t1.motivated_by_discovery_ids == [d1.discovery_id]
    assert t2.motivated_by_discovery_ids == [d2.discovery_id]
    assert set(t3.motivated_by_discovery_ids) == {d1.discovery_id, d2.discovery_id}
    assert t3.profile_id == profile.profile_id
    assert t3.variables == ["monthly_spend", "churned"]
    assert t3.evidence_expectation == "A deterministic p-value."
    assert t3.analytical_specification is not None
    assert t3.analytical_specification.data_profile_id == profile.profile_id
    replayed_decomposition = _approve_operation_batch(
        database_url,
        session_id_decomp,
        proposal_decomp.pending_interaction,
    )
    assert replayed_decomposition.committed_operation_ids == []
    assert len(TaskRepository(db_session).list(parent_task_id=t0.task_id)) == 3

    # 3. Execute T3 via /execute and dispatcher
    session_id_exec = "step10-e2e-execution"
    proposed_exec = _run_planner(
        database_url,
        f"/execute {t3.task_id}",
        Context(session_id=session_id_exec),
    )
    assert proposed_exec.pending_interaction is not None
    assert proposed_exec.pending_interaction.kind == "execution_approval"
    
    admitted = _run_planner(
        database_url,
        "/approve",
        Context(session_id=session_id_exec),
        PlannerDecision(
            action="approve",
            proposal_id=proposed_exec.pending_interaction.proposal_id,
            execution_ref=proposed_exec.pending_interaction.payload["execution_ref"],
        ),
    )
    assert admitted.controlled_error is None
    assert admitted.executor_dispatch_ref is not None

    db_session.expire_all()
    hypotheses = HypothesisRepository(db_session).list(task_id=t3.task_id)
    assert len(hypotheses) == 1
    h3 = hypotheses[0]
    runs = ExecutionRunRepository(db_session).list(task_id=t3.task_id)
    assert len(runs) == 1
    a1 = runs[0]
    
    # 4. Fail the execution first to verify retry loop (Lower Half)
    failing_executor = DeterministicExecutor(fail=True)
    dispatch_session = get_session(database_url)
    try:
        assert asyncio.run(
            dispatch_pending_attempts(
                dispatch_session,
                _dispatcher_for(failing_executor),
                "worker-a1",
            )
        ) == 1
    finally:
        dispatch_session.close()
        
    finalizer_session = get_session(database_url)
    try:
        assert finalize_attempt(finalizer_session, a1.execution_run_id)
        assert finalize_attempt(finalizer_session, a1.execution_run_id)
    finally:
        finalizer_session.close()

    retry_session = get_session(database_url)
    try:
        a2_id = authorize_retry(retry_session, a1.execution_run_id, "technical_retry")
    finally:
        retry_session.close()
    assert a2_id is not None
    repeated_retry_session = get_session(database_url)
    try:
        assert authorize_retry(
            repeated_retry_session,
            a1.execution_run_id,
            "technical_retry",
        ) == a2_id
    finally:
        repeated_retry_session.close()

    successful_executor = DeterministicExecutor()
    dispatch_success_session = get_session(database_url)
    try:
        assert asyncio.run(
            dispatch_pending_attempts(
                dispatch_success_session,
                _dispatcher_for(successful_executor),
                "worker-a2",
            )
        ) == 1
    finally:
        dispatch_success_session.close()

    duplicate_session = get_session(database_url)
    try:
        a2 = ExecutionRunRepository(duplicate_session).get_by_id(a2_id)
        assert a2 is not None
        submit_execution_result(
            duplicate_session,
            execution_run_id=a2.execution_run_id,
            dispatch_idempotency_key=a2.dispatch_idempotency_key,
            lease_epoch=a2.lease_epoch,
            worker_id="worker-a2",
            method_id=a2.method_id,
            executor_status="completed",
            result=successful_executor.results[0],
        )
    finally:
        duplicate_session.close()

    success_finalizer_session = get_session(database_url)
    try:
        assert finalize_attempt(success_finalizer_session, a2_id)
        assert finalize_attempt(success_finalizer_session, a2_id)
    finally:
        success_finalizer_session.close()

    # 5. Review discoveries
    read_session = get_session(database_url)
    try:
        runs = ExecutionRunRepository(read_session).list(task_id=t3.task_id)
        assert len(runs) == 2
        persisted_a2 = next(run for run in runs if run.execution_run_id == a2_id)
        assert persisted_a2.status == ExecutionRunStatus.COMPLETED
        assert persisted_a2.previous_attempt_id == a1.execution_run_id
        assert persisted_a2.task_id == a1.task_id == t3.task_id
        assert persisted_a2.hypothesis_id == a1.hypothesis_id == h3.hypothesis_id
        assert persisted_a2.method_id == a1.method_id
        assert persisted_a2.parameter_hash == a1.parameter_hash
        assert persisted_a2.dispatch_idempotency_key != a1.dispatch_idempotency_key
        assert len(ExecutionOutboxRepository(read_session).list()) == 2
        assert len(failing_executor.requests) == len(successful_executor.requests) == 1
        
        evidence = EvidenceRepository(read_session).list(hypothesis_id=h3.hypothesis_id)
        discoveries = DiscoveryRepository(read_session).list(hypothesis_id=h3.hypothesis_id)
        assert len(evidence) == 1
        assert len(discoveries) == 1
        e3, d3 = evidence[0], discoveries[0]
        assert d3.evidence_ids == [e3.evidence_id]
        assert e3.hypothesis_id == d3.hypothesis_id == h3.hypothesis_id
        assert t3.parent_task_id == t0.task_id
        assert HypothesisRepository(read_session).list(task_id=t0.task_id) == []
        assert HypothesisRepository(read_session).list(task_id=t1.task_id) == []
        assert HypothesisRepository(read_session).list(task_id=t2.task_id) == []

        # Epistemic barrier assertion
        executor_input = successful_executor.requests[0]
        forbidden_values = [
            assumption.statement,
            str(d1.discovery_id),
            str(d2.discovery_id),
        ]
        scientific_payloads = [
            executor_input.model_dump_json(),
            h3.model_dump_json(),
            e3.model_dump_json(),
            d3.model_dump_json(),
        ]
        assert all(
            value not in payload
            for value in forbidden_values
            for payload in scientific_payloads
        )
    finally:
        read_session.close()

    # 6. Verify Review Propagation
    discovery_repository = DiscoveryRepository(db_session)
    EvidenceRepository(db_session).invalidate(
        e1.evidence_id,
        reason="D1 bootstrap evidence invalidated for review.",
        discovery_repository=discovery_repository,
    )
    propagate_discovery_review(db_session, d1.discovery_id)
    db_session.commit()
    db_session.expire_all()
    assert discovery_repository.get_by_id(d1.discovery_id).lifecycle_state == (
        DiscoveryLifecycleState.FLAGGED
    )
    assert TaskRepository(db_session).get_by_id(t0.task_id).review_reasons
    assert TaskRepository(db_session).get_by_id(t1.task_id).review_reasons
    assert TaskRepository(db_session).get_by_id(t3.task_id).review_reasons
    assert TaskRepository(db_session).get_by_id(t2.task_id).review_reasons == []

    db_session.expire_all()
    persisted_d3 = DiscoveryRepository(db_session).get_by_id(d3.discovery_id)
    assert persisted_d3 is not None
    assert persisted_d3.lifecycle_state == DiscoveryLifecycleState.ACTIVE
    continuity = DiscoveryRetrievalEngine(db_session).retrieve(
        RetrievalRequest(
            objective_id=objective.objective_id,
            active_data_profile_id=profile.profile_id,
            session_frame_id=root_successor.session_frame_id,
            parent_task_id=t3.task_id,
            query_text=persisted_d3.claim.statement,
        ),
        root_successor,
    )
    motivation_ids = {item.discovery_id for item in continuity.motivation_candidates}
    assert d3.discovery_id in motivation_ids
    assert d1.discovery_id not in motivation_ids

    # Done.


def test_root_motivation_rejects_raw_uuid_context_only_and_stale_selection(db_session) -> None:
    database_url = _database_url(db_session)
    objective = _create_objective_through_public_approval(db_session, "step10-root-guards")
    profile = DataProfileRepository(db_session).create(_profile())
    d1, e1 = _bootstrap_discovery(db_session, profile, 1)
    d2, e2 = _bootstrap_discovery(db_session, profile, 2)
    EvidenceRepository(db_session).invalidate(
        e2.evidence_id,
        reason="Make D2 contextual-only.",
        discovery_repository=DiscoveryRepository(db_session),
    )
    frame = SessionFrameRepository(db_session).create(
        SessionFrameBuilder().build(
            objective=objective,
            data_profiles=[profile],
            discoveries=[d1, d2],
            evidence=[e1, e2],
        )
    )

    for session_id, model in (
        ("step10-raw-uuid", RawUuidRootTaskModel(d1.discovery_id)),
        ("step10-context-only", ContextOnlyRootTaskModel()),
    ):
        rejected = _run_planner(
            database_url,
            "/manage_task create root task",
            Context(
                session_id=session_id,
                session_frame_id=frame.session_frame_id,
                task_management_model=model,
            ),
        )
        assert rejected.pending_interaction is None
        assert rejected.controlled_error is not None
        assert rejected.controlled_error.code == "invalid_task_proposal_reference"

    stale_model = FirstCandidateRootTaskModel()
    stale_proposal = _run_planner(
        database_url,
        "/manage_task create root task",
        Context(
            session_id="step10-stale-root",
            session_frame_id=frame.session_frame_id,
            task_management_model=stale_model,
        ),
    )
    assert stale_proposal.pending_interaction is not None
    before_frames = SessionFrameRepository(db_session).list_recent(limit=20)
    EvidenceRepository(db_session).invalidate(
        e1.evidence_id,
        reason="Invalidate D1 after proposal.",
        discovery_repository=DiscoveryRepository(db_session),
    )
    stale_commit = _approve_operation_batch(
        database_url,
        "step10-stale-root",
        stale_proposal.pending_interaction,
    )
    assert stale_commit.commit_result is not None
    assert not stale_commit.commit_result.succeeded
    assert all(task.title != "Stale T0" for task in TaskRepository(db_session).list())
    assert SessionFrameRepository(db_session).list_recent(limit=20) == before_frames

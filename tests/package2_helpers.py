"""Durable Package 2 lineage fixtures shared by focused adversarial tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from sqlmodel import Session

from application.execution.identity import method_parameter_hash
from application.governance import (
    ALLOWED_TRUSTED_OPERATION_TYPES,
    ALLOWED_TRUSTED_PURPOSES,
    USER_GOVERNED_OPERATION_TYPE,
    USER_GOVERNED_PURPOSE,
    compute_governance_authority_fingerprint,
)
from application.orchestrator.validity_propagation_service import (
    AtomicValidityPropagationService,
    validity_authority_scope,
)
from db.models import (
    ExecutionOutboxRecord,
    ExecutionRunRecord,
    GovernanceAuthorityRecord,
    utc_now,
)
from repositories.analysis_frame_repository import AnalysisFrameRepository
from repositories.data_profile_repository import DataProfileRepository
from repositories.evidence_repository import EvidenceRepository
from repositories.hypothesis_repository import HypothesisRepository
from repositories.task_repository import TaskRepository
from schemas.artifacts import AnalyticalSpecification, DataProfile, Evidence, Hypothesis, Task
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
    AnalysisIntent,
    AuthorizationClass,
    DataProfileLifecycleState,
    DataProfileMethod,
    DatasetSourceType,
    DiscoveryEpistemicStatus,
    EvidenceType,
    ExecutionRunStatus,
    HypothesisStatus,
    TaskKind,
    TaskLifecycleState,
    ValidityEventType,
    ValiditySourceType,
)
from schemas.evaluation import DiscoveryProposal, DiscoverySynthesisBundle
from schemas.execution.contracts import (
    ExecutionSpecification,
    HypothesisDraft,
    PreparedExecution,
)
from schemas.provenance import AnalysisFrame
from schemas.validity_propagation_contracts import ValidityPropagationCommand


@dataclass(frozen=True, slots=True)
class Package2Lineage:
    profile_id: UUID
    task_id: UUID
    hypothesis_id: UUID
    analysis_frame_id: UUID
    execution_run_id: UUID
    evidence_id: UUID


def persist_governance_authority(
    session: Session,
    *,
    authority_class: AuthorizationClass = AuthorizationClass.USER_GOVERNED,
    actor_identity: str = "user:lead_researcher",
    workspace_id: str = "workspace:test",
    session_id: str | None = "session:test",
    purpose: str | None = None,
    operation_type: str | None = None,
    active: bool = True,
) -> GovernanceAuthorityRecord:
    """Seed an independently issued durable authority grant for governance tests."""

    if authority_class == AuthorizationClass.TRUSTED_INTERNAL:
        session_id = None
        purpose = purpose or next(iter(sorted(ALLOWED_TRUSTED_PURPOSES)))
        operation_type = operation_type or next(iter(sorted(ALLOWED_TRUSTED_OPERATION_TYPES)))
    else:
        purpose = purpose or USER_GOVERNED_PURPOSE
        operation_type = operation_type or USER_GOVERNED_OPERATION_TYPE
    authority_id = uuid4()
    issued_at = utc_now()
    expires_at = issued_at + timedelta(hours=1)
    fingerprint = compute_governance_authority_fingerprint(
        authority_id=authority_id,
        actor_identity=actor_identity,
        authority_class=authority_class,
        workspace_id=workspace_id,
        session_id=session_id,
        purpose=purpose,
        operation_type=operation_type,
        issued_by="auth:test-issuer",
        issued_at=issued_at,
        expires_at=expires_at,
    )
    record = GovernanceAuthorityRecord(
        authority_id=authority_id,
        actor_identity=actor_identity,
        authority_class=authority_class,
        workspace_id=workspace_id,
        session_id=session_id,
        purpose=purpose,
        operation_type=operation_type,
        issued_by="auth:test-issuer",
        issued_at=issued_at,
        expires_at=expires_at,
        active=active,
        authority_fingerprint=fingerprint,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def propagate_validity_for_test(
    session: Session,
    *,
    source_type: ValiditySourceType,
    source_id: UUID,
    event_type: ValidityEventType,
    reason: str,
    idempotency_key: str,
    replacement_id: UUID | None = None,
    workspace_id: str = "workspace:test",
):
    """Execute the real Package 4 boundary with a persisted test issuer grant."""

    purpose, operation_type = validity_authority_scope(
        event_type=event_type,
        source_type=source_type,
        source_id=source_id,
        replacement_id=replacement_id,
    )
    grant = persist_governance_authority(
        session,
        authority_class=AuthorizationClass.TRUSTED_INTERNAL,
        actor_identity="system_integrity",
        workspace_id=workspace_id,
        session_id=None,
        purpose=purpose,
        operation_type=operation_type,
    )
    service = AtomicValidityPropagationService(session)
    source_state, source_fingerprint = service.load_source_guard(source_type, source_id)
    replacement_fingerprint = None
    if replacement_id is not None:
        _, replacement_fingerprint = service.load_source_guard(
            source_type,
            replacement_id,
        )
    command = ValidityPropagationCommand(
        source_type=source_type,
        source_id=source_id,
        event_type=event_type,
        reason=reason,
        authority_id=grant.authority_id,
        workspace_id=workspace_id,
        expected_source_state=source_state,
        expected_source_fingerprint=source_fingerprint,
        idempotency_key=idempotency_key,
        replacement_id=replacement_id,
        expected_replacement_fingerprint=replacement_fingerprint,
    )
    return service.execute_propagation(command)


def proposal_for_bundle(
    bundle: DiscoverySynthesisBundle,
    *,
    epistemic_status: DiscoveryEpistemicStatus = DiscoveryEpistemicStatus.SUPPORTED,
) -> DiscoveryProposal:
    """Return a fully aligned proposal suitable for PydanticAI test-model output."""

    if epistemic_status in {
        DiscoveryEpistemicStatus.INCONCLUSIVE,
        DiscoveryEpistemicStatus.INSUFFICIENT_EVIDENCE,
    }:
        statement = (
            "Available evidence is insufficient to establish the approved association within scope."
        )
    elif epistemic_status == DiscoveryEpistemicStatus.CONTRADICTED:
        statement = "Observed evidence contradicts the approved association within scope."
    else:
        statement = "Observed evidence supports the approved association within scope."
    evidence_ids = [evidence.evidence_id for evidence in bundle.admitted_evidence]
    limitations = tuple(
        limitation for evidence in bundle.admitted_evidence for limitation in evidence.limitations
    )
    return DiscoveryProposal(
        claim=DiscoveryClaim(
            statement=statement,
            scope=bundle.hypothesis.scope,
            result="The observed result was interpreted under the approved decision rule.",
        ),
        epistemic_status=epistemic_status,
        scope=bundle.hypothesis.scope,
        evidence_ids=evidence_ids,
        validity_basis=ValidityBasis(
            data_profile_id=bundle.data_profile.data_profile_id,
            analysis_frame_refs=[
                frame.frame_ref or str(frame.analysis_frame_id) for frame in bundle.analysis_frames
            ],
            hypothesis_id=bundle.hypothesis.hypothesis_id,
            evidence_ids=evidence_ids,
            method=bundle.hypothesis.validation_method,
            parameters=[parameter.to_domain() for parameter in bundle.hypothesis.method_parameters],
            decision_rule=bundle.hypothesis.decision_rule.to_domain(),
            strength="moderate",
            uncertainty="Sampling and method limitations remain within the stated scope.",
            assumptions_excluded_from_inference=True,
            invalidators=list(bundle.required_invalidators),
        ),
        limitations=limitations,
    )


def persist_package2_lineage(
    session: Session,
    *,
    p_value: float = 0.01,
    task_title: str = "Evaluate the approved association",
    task_description: str = "Workflow wording excluded from scientific synthesis.",
    evidence_limitations: tuple[str, ...] = ("Limited to complete cases.",),
) -> Package2Lineage:
    """Persist one complete admitted-Evidence lineage through canonical repositories."""

    profile = DataProfileRepository(session).create(
        DataProfile(
            dataset_path="data/protected.csv",
            source_type=DatasetSourceType.FILE,
            dvc_hash="dvc:protected-v1",
            method=DataProfileMethod.INFERRED_SCHEMA,
            schema_summary=SchemaSummary(column_order=["x", "y"]),
            baseline_summary=BaselineSummary(column_names=["x", "y"]),
            row_count=120,
            column_count=2,
            lifecycle_state=DataProfileLifecycleState.ACTIVE,
            accepted_as_ground_truth=True,
        )
    )
    parameters = [MethodParameter(name="alpha", value=0.05)]
    decision_rule = EvaluationThresholds(p_value=0.05)
    specification = AnalyticalSpecification(
        hypothesis_statement="X is associated with Y in the accepted profile.",
        claim_type="association",
        analysis_intent=AnalysisIntent.CONFIRMATORY,
        data_profile_id=profile.profile_id,
        variable_bindings=["x", "y"],
        scope="Accepted complete-case rows in profile v1.",
        evidence_expectation="A finite p-value from the approved method.",
        decision_rule=decision_rule,
        validation_method="pearson_correlation",
        executor_id="deterministic",
        method_parameters=parameters,
        deterministic_seed=17,
    )
    task = TaskRepository(session).create(
        Task(
            title=task_title,
            description=task_description,
            lifecycle_state=TaskLifecycleState.ACTIVE,
            task_kind=TaskKind.ANALYTICAL,
            profile_id=profile.profile_id,
            variables=["x", "y"],
            evidence_expectation=specification.evidence_expectation,
            analytical_specification=specification,
        )
    )
    hypothesis = HypothesisRepository(session).create(
        Hypothesis(
            task_id=task.task_id,
            profile_id=profile.profile_id,
            statement=specification.hypothesis_statement,
            analysis_intent=specification.analysis_intent,
            variables=list(specification.variable_bindings),
            scope=specification.scope,
            validation_method=specification.validation_method,
            evidence_expectation=specification.evidence_expectation,
            status=HypothesisStatus.READY_FOR_EVALUATION,
        )
    )
    frame = AnalysisFrameRepository(session).create(
        AnalysisFrame(
            data_profile_id=profile.profile_id,
            frame_hash="frame:protected-v1",
            frame_ref="analysis-frame:protected-v1",
            column_refs=["x", "y"],
            row_filter_description="complete cases",
        )
    )

    run_id = uuid4()
    parameter_hash = method_parameter_hash(parameters)
    prepared = PreparedExecution(
        task_ref=str(task.task_id),
        data_profile_ref=str(profile.profile_id),
        hypothesis_ref=str(hypothesis.hypothesis_id),
        execution_run_ref=str(run_id),
        task_title=task.title,
        dataset_path=profile.dataset_path,
        hypothesis=HypothesisDraft(
            statement=hypothesis.statement,
            variables=list(hypothesis.variables),
            scope=hypothesis.scope,
            validation_method=hypothesis.validation_method,
            evidence_expectation=hypothesis.evidence_expectation,
        ),
        specification=ExecutionSpecification(
            claim_type=specification.claim_type,
            variable_bindings=list(specification.variable_bindings),
            scope=specification.scope,
            evidence_expectation=specification.evidence_expectation,
            decision_rule=decision_rule,
            validation_method=specification.validation_method,
            executor_id=specification.executor_id,
            method_parameters=parameters,
        ),
        deterministic_seed=specification.deterministic_seed,
        contract_fingerprint="approved-contract-v1",
        execution_run_id=run_id,
        dispatch_idempotency_key=f"dispatch:{run_id}",
        lease_epoch=1,
    )
    run_record = ExecutionRunRecord(
        execution_run_id=run_id,
        task_id=task.task_id,
        hypothesis_id=hypothesis.hypothesis_id,
        analysis_frame_id=frame.analysis_frame_id,
        executor_type=specification.executor_id,
        method_id=specification.validation_method,
        parameter_hash=parameter_hash,
        status=ExecutionRunStatus.EVIDENCE_ADMITTED,
        dispatch_idempotency_key=prepared.dispatch_idempotency_key,
        lease_epoch=1,
        attempt_version=4,
    )
    session.add(run_record)
    session.flush()
    session.add(
        ExecutionOutboxRecord(
            execution_run_id=run_id,
            dispatch_idempotency_key=prepared.dispatch_idempotency_key or "",
            executor_type=specification.executor_id,
            method_id=specification.validation_method,
            parameter_hash=parameter_hash,
            prepared_payload=prepared.model_dump(mode="json"),
            status="processed",
        )
    )
    session.commit()

    evidence_repository = EvidenceRepository(session, strict_provenance_validation=True)
    evidence_seed = Evidence(
        hypothesis_id=hypothesis.hypothesis_id,
        profile_id=profile.profile_id,
        analysis_frame_ref=str(frame.analysis_frame_id),
        execution_run_ref=str(run_id),
        evidence_type=EvidenceType.STATISTICAL_TEST,
        method=specification.validation_method,
        parameters=parameters,
        provenance=EvidenceProvenance(
            analysis_frame_ref=str(frame.analysis_frame_id),
            execution_run_ref=str(run_id),
            code_reference="git:approved-code",
            environment_reference="lock:approved-env",
            artifact_paths=["artifacts/result.json"],
        ),
        result_summary=EvidenceResultSummary(
            summary=f"Approved method observed p={p_value}.",
            metric_name="p_value",
            metric_value=p_value,
        ),
        artifact_refs=["artifacts/result.json"],
        limitations=list(evidence_limitations),
    )
    evidence_repository._stage_create_from_evidence_admission(evidence_seed)
    session.commit()
    evidence = evidence_repository.get_by_id(evidence_seed.evidence_id)
    if evidence is None:
        raise AssertionError("Package 2 test lineage failed to seed Evidence.")
    return Package2Lineage(
        profile_id=profile.profile_id,
        task_id=task.task_id,
        hypothesis_id=hypothesis.hypothesis_id,
        analysis_frame_id=frame.analysis_frame_id,
        execution_run_id=run_id,
        evidence_id=evidence.evidence_id,
    )

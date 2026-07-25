"""Canonical protected-bundle construction from durable repository authority."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from application.execution.identity import method_parameter_hash
from db.models import DiscoveryRecord
from repositories.evidence import AnalysisFrameRepository, EvidenceRepository
from repositories.execution import ExecutionOutboxRepository, ExecutionRunRepository
from repositories.research import DataProfileRepository, HypothesisRepository, TaskRepository
from schemas.canonical import canonical_sha256
from schemas.enums import (
    DataProfileLifecycleState,
    EvidenceLifecycleState,
    ExecutionRunStatus,
    HypothesisStatus,
    TaskKind,
    TaskLifecycleState,
    ValiditySourceState,
)
from schemas.evaluation import (
    SUPPORTED_EVALUATION_CONTRACT_VERSION,
    ActiveStateProof,
    AdmittedEvidenceSnapshot,
    AnalysisFrameEvaluationSnapshot,
    BundleProvenanceManifest,
    DataProfileEvaluationSnapshot,
    DecisionRuleSnapshot,
    DiscoverySynthesisBundle,
    EvidenceResultSnapshot,
    ExecutionRunEvaluationSnapshot,
    HypothesisEvaluationSnapshot,
    InclusionRole,
    ManifestObjectType,
    MethodParameterSnapshot,
    ProvenanceManifestEntry,
    RepositorySource,
)
from schemas.evidence import Evidence
from schemas.execution.contracts import PreparedExecution
from schemas.research import AnalyticalSpecification, Hypothesis, Task

REQUIRED_INVALIDATORS = (
    "DataProfile identity or accepted-ground-truth state changes.",
    "Any admitted Evidence is superseded or invalidated.",
    "Approved method, parameters, decision rule, scope, or AnalysisFrame changes.",
)


class SynthesisBundleError(ValueError):
    """Raised when durable state cannot form an admissible protected bundle."""


def compute_bundle_digest(bundle: DiscoverySynthesisBundle) -> str:
    """Digest complete scientific input while excluding the digest field itself."""

    return canonical_sha256(bundle.model_dump(mode="python", exclude={"input_digest"}))


def compute_evidence_set_digest(bundle: DiscoverySynthesisBundle) -> str:
    """Bind the exact active Evidence identities and immutable fingerprints."""

    return canonical_sha256(
        [
            {
                "evidence_id": evidence.evidence_id,
                "evidence_fingerprint": evidence.evidence_fingerprint,
            }
            for evidence in bundle.admitted_evidence
        ]
    )


def compute_evaluation_key(bundle: DiscoverySynthesisBundle) -> str:
    """Bind Hypothesis, exact Evidence set, bundle digest, and contract version."""

    return canonical_sha256(
        {
            "hypothesis_id": bundle.hypothesis.hypothesis_id,
            "evidence_set_digest": compute_evidence_set_digest(bundle),
            "bundle_digest": bundle.input_digest,
            "contract_version": bundle.contract_version,
        }
    )


def build_synthesis_bundle(
    session: Session,
    hypothesis_id: UUID,
    *,
    contract_version: str = SUPPORTED_EVALUATION_CONTRACT_VERSION,
    allow_evaluated: bool = False,
) -> tuple[DiscoverySynthesisBundle, BundleProvenanceManifest]:
    """Build one protected bundle exclusively from current durable repositories."""

    if contract_version != SUPPORTED_EVALUATION_CONTRACT_VERSION:
        raise SynthesisBundleError(f"Unsupported evaluation contract version: {contract_version}.")

    session.expire_all()
    hypothesis = HypothesisRepository(session).get_by_id(hypothesis_id)
    if hypothesis is None:
        raise SynthesisBundleError(f"Hypothesis does not exist: {hypothesis_id}.")
    allowed_statuses = (
        {HypothesisStatus.READY_FOR_EVALUATION, HypothesisStatus.EVALUATED}
        if allow_evaluated
        else {HypothesisStatus.READY_FOR_EVALUATION}
    )
    if hypothesis.status not in allowed_statuses:
        raise SynthesisBundleError("Hypothesis must be READY_FOR_EVALUATION.")

    task = TaskRepository(session).get_by_id(hypothesis.task_id)
    if task is None:
        raise SynthesisBundleError("Hypothesis source Task does not exist.")
    allowed_task_states = (
        {TaskLifecycleState.ACTIVE, TaskLifecycleState.COMPLETED}
        if allow_evaluated
        else {TaskLifecycleState.ACTIVE}
    )
    if task.lifecycle_state not in allowed_task_states or task.task_kind != TaskKind.ANALYTICAL:
        raise SynthesisBundleError("Hypothesis source Task is not active analytical work.")
    if TaskRepository(session).list(parent_task_id=task.task_id):
        raise SynthesisBundleError("Only terminal analytical Tasks are evaluation-eligible.")
    if task.analytical_specification is None:
        raise SynthesisBundleError("Task lacks its durable approved analytical specification.")
    specification = AnalyticalSpecification.model_validate(task.analytical_specification)
    _validate_approved_hypothesis_contract(hypothesis, task, specification)

    data_profile = DataProfileRepository(session).get_by_id(hypothesis.profile_id)
    if data_profile is None:
        raise SynthesisBundleError("Hypothesis DataProfile does not exist.")
    if (
        data_profile.lifecycle_state != DataProfileLifecycleState.ACTIVE
        or not data_profile.accepted_as_ground_truth
    ):
        raise SynthesisBundleError("DataProfile must be active and accepted as ground truth.")
    if not allow_evaluated:
        existing_discovery_id = session.exec(
            select(DiscoveryRecord.discovery_id)
            .where(DiscoveryRecord.hypothesis_id == hypothesis_id)
            .limit(1)
        ).first()
        if existing_discovery_id is not None:
            raise SynthesisBundleError("A Discovery already exists for this Hypothesis.")

    active_evidence = EvidenceRepository(session).list(
        hypothesis_id=hypothesis_id,
        lifecycle_state=EvidenceLifecycleState.ACTIVE,
    )
    if not active_evidence:
        raise SynthesisBundleError("At least one active admitted Evidence record is required.")
    active_evidence.sort(key=lambda item: str(item.evidence_id))

    frame_snapshots: dict[UUID, AnalysisFrameEvaluationSnapshot] = {}
    run_snapshots: dict[UUID, ExecutionRunEvaluationSnapshot] = {}
    evidence_snapshots: list[AdmittedEvidenceSnapshot] = []
    for evidence in active_evidence:
        evidence_snapshot, frame_snapshot, run_snapshot = _build_evidence_lineage(
            session=session,
            evidence=evidence,
            hypothesis_id=hypothesis_id,
            task_id=task.task_id,
            profile_id=data_profile.profile_id,
            specification=specification,
        )
        prior_frame = frame_snapshots.setdefault(frame_snapshot.analysis_frame_id, frame_snapshot)
        prior_run = run_snapshots.setdefault(run_snapshot.execution_run_id, run_snapshot)
        if prior_frame != frame_snapshot or prior_run != run_snapshot:
            raise SynthesisBundleError("Conflicting durable provenance snapshots were found.")
        evidence_snapshots.append(evidence_snapshot)

    profile_fingerprint = canonical_sha256(
        data_profile.model_dump(mode="python", exclude={"created_at"})
    )
    hypothesis_snapshot = HypothesisEvaluationSnapshot(
        hypothesis_id=hypothesis.hypothesis_id,
        data_profile_id=hypothesis.profile_id,
        statement=hypothesis.statement,
        analysis_intent=hypothesis.analysis_intent,
        variables=tuple(hypothesis.variables),
        scope=hypothesis.scope,
        validation_method=hypothesis.validation_method,
        method_parameters=tuple(
            MethodParameterSnapshot(name=parameter.name, value=parameter.value)
            for parameter in specification.method_parameters
        ),
        decision_rule=DecisionRuleSnapshot.from_domain(specification.decision_rule),
        deterministic_seed=specification.deterministic_seed,
        evidence_expectation=hypothesis.evidence_expectation,
    )
    profile_snapshot = DataProfileEvaluationSnapshot(
        data_profile_id=data_profile.profile_id,
        source_type=data_profile.source_type,
        version_fingerprint=profile_fingerprint,
        dvc_hash=data_profile.dvc_hash,
        dvc_version_label=data_profile.dvc_version_label,
        row_count=data_profile.row_count,
        column_count=data_profile.column_count,
        accepted_as_ground_truth=True,
    )

    unsigned = DiscoverySynthesisBundle(
        contract_version="1.0",
        hypothesis=hypothesis_snapshot,
        data_profile=profile_snapshot,
        analysis_frames=tuple(
            frame_snapshots[frame_id] for frame_id in sorted(frame_snapshots, key=str)
        ),
        execution_runs=tuple(run_snapshots[run_id] for run_id in sorted(run_snapshots, key=str)),
        admitted_evidence=tuple(evidence_snapshots),
        required_invalidators=REQUIRED_INVALIDATORS,
        input_digest="0" * 64,
    )
    digest = compute_bundle_digest(unsigned)
    bundle = unsigned.model_copy(update={"input_digest": digest})
    manifest = _build_provenance_manifest(bundle)
    return bundle, manifest


def _validate_approved_hypothesis_contract(
    hypothesis: Hypothesis,
    task: Task,
    specification: AnalyticalSpecification,
) -> None:
    if (
        specification.data_profile_id != hypothesis.profile_id
        or task.profile_id != hypothesis.profile_id
        or specification.hypothesis_statement != hypothesis.statement
        or specification.analysis_intent != hypothesis.analysis_intent
        or specification.variable_bindings != hypothesis.variables
        or specification.variable_bindings != task.variables
        or specification.scope != hypothesis.scope
        or specification.validation_method != hypothesis.validation_method
        or specification.evidence_expectation != hypothesis.evidence_expectation
        or specification.evidence_expectation != task.evidence_expectation
    ):
        raise SynthesisBundleError(
            "Durable Hypothesis/Task content disagrees with the approved analytical specification."
        )


def _build_evidence_lineage(
    *,
    session: Session,
    evidence: Evidence,
    hypothesis_id: UUID,
    task_id: UUID,
    profile_id: UUID,
    specification: AnalyticalSpecification,
) -> tuple[
    AdmittedEvidenceSnapshot,
    AnalysisFrameEvaluationSnapshot,
    ExecutionRunEvaluationSnapshot,
]:
    try:
        frame_id = UUID(evidence.analysis_frame_ref)
        run_id = UUID(evidence.execution_run_ref)
    except ValueError as exc:
        raise SynthesisBundleError(
            "Evidence provenance references must be canonical durable UUIDs."
        ) from exc

    frame = AnalysisFrameRepository(session).get_by_id(frame_id)
    run = ExecutionRunRepository(session).get_by_id(run_id)
    if frame is None or run is None:
        raise SynthesisBundleError("Evidence references missing AnalysisFrame or ExecutionRun.")
    if (
        evidence.hypothesis_id != hypothesis_id
        or evidence.profile_id != profile_id
        or frame.data_profile_id != profile_id
        or run.task_id != task_id
        or run.hypothesis_id != hypothesis_id
        or run.analysis_frame_id != frame_id
        or run.status != ExecutionRunStatus.EVIDENCE_ADMITTED
        or frame.validity_state != ValiditySourceState.ACTIVE
        or run.validity_state != ValiditySourceState.ACTIVE
        or not run.executor_type
        or not run.method_id
        or not run.parameter_hash
        or evidence.method != specification.validation_method
        or evidence.method != run.method_id
        or evidence.parameters != specification.method_parameters
        or method_parameter_hash(evidence.parameters) != run.parameter_hash
    ):
        raise SynthesisBundleError("Evidence and admitted execution provenance do not match.")

    outboxes = ExecutionOutboxRepository(session).list(execution_run_id=run_id)
    if len(outboxes) != 1:
        raise SynthesisBundleError("ExecutionRun must have exactly one durable outbox contract.")
    outbox = outboxes[0]
    if (
        outbox.status != "processed"
        or outbox.executor_type != run.executor_type
        or outbox.method_id != run.method_id
        or outbox.parameter_hash != run.parameter_hash
    ):
        raise SynthesisBundleError("ExecutionRun outbox authority is incomplete or mismatched.")
    try:
        prepared = PreparedExecution.model_validate(outbox.prepared_payload)
    except ValueError as exc:
        raise SynthesisBundleError("Durable outbox contains an invalid approved contract.") from exc
    if (
        prepared.specification != _execution_specification(specification)
        or prepared.deterministic_seed != specification.deterministic_seed
    ):
        raise SynthesisBundleError(
            "Outbox execution contract differs from the durable Task contract."
        )

    frame_fingerprint = canonical_sha256(frame.model_dump(mode="python", exclude={"created_at"}))
    frame_snapshot = AnalysisFrameEvaluationSnapshot(
        analysis_frame_id=frame.analysis_frame_id,
        data_profile_id=frame.data_profile_id,
        frame_fingerprint=frame_fingerprint,
        frame_hash=frame.frame_hash,
        frame_ref=frame.frame_ref,
        column_refs=tuple(frame.column_refs),
        row_filter_description=frame.row_filter_description,
    )
    run_snapshot = ExecutionRunEvaluationSnapshot(
        execution_run_id=run.execution_run_id,
        task_id=task_id,
        hypothesis_id=hypothesis_id,
        analysis_frame_id=frame_id,
        executor_type=run.executor_type,
        method_id=run.method_id,
        parameter_hash=run.parameter_hash,
        attempt_version=run.attempt_version,
        run_fingerprint=canonical_sha256(
            {
                "execution_run_id": run.execution_run_id,
                "task_id": task_id,
                "hypothesis_id": hypothesis_id,
                "analysis_frame_id": frame_id,
                "executor_type": run.executor_type,
                "method_id": run.method_id,
                "parameter_hash": run.parameter_hash,
                "attempt_version": run.attempt_version,
                "status": ExecutionRunStatus.EVIDENCE_ADMITTED,
            }
        ),
        status="evidence_admitted",
    )

    evidence_fingerprint = canonical_sha256(
        evidence.model_dump(mode="python", exclude={"created_at"})
    )
    result = evidence.result_summary
    evidence_snapshot = AdmittedEvidenceSnapshot(
        evidence_id=evidence.evidence_id,
        hypothesis_id=evidence.hypothesis_id,
        data_profile_id=evidence.profile_id,
        analysis_frame_id=frame_id,
        execution_run_id=run_id,
        evidence_type=evidence.evidence_type,
        method=evidence.method,
        parameters=tuple(
            MethodParameterSnapshot(name=parameter.name, value=parameter.value)
            for parameter in evidence.parameters
        ),
        result=EvidenceResultSnapshot(
            summary=result.summary,
            key_findings=tuple(result.key_findings),
            metric_name=result.metric_name,
            metric_value=result.metric_value,
            metric_unit=result.metric_unit,
        ),
        limitations=tuple(evidence.limitations),
        code_reference=evidence.provenance.code_reference,
        environment_reference=evidence.provenance.environment_reference,
        evidence_fingerprint=evidence_fingerprint,
        lifecycle_state="active",
    )
    return evidence_snapshot, frame_snapshot, run_snapshot


def _execution_specification(specification: AnalyticalSpecification) -> object:
    from schemas.execution.contracts import ExecutionSpecification

    return ExecutionSpecification(
        claim_type=specification.claim_type,
        variable_bindings=list(specification.variable_bindings),
        scope=specification.scope,
        evidence_expectation=specification.evidence_expectation,
        decision_rule=specification.decision_rule,
        validation_method=specification.validation_method,
        executor_id=specification.executor_id,
        method_parameters=list(specification.method_parameters),
    )


def _build_provenance_manifest(
    bundle: DiscoverySynthesisBundle,
) -> BundleProvenanceManifest:
    entries: list[ProvenanceManifestEntry] = [
        ProvenanceManifestEntry(
            object_type=ManifestObjectType.HYPOTHESIS,
            object_id=bundle.hypothesis.hypothesis_id,
            version_or_fingerprint=canonical_sha256(bundle.hypothesis),
            inclusion_role=InclusionRole.EVALUAND,
            repository_source=RepositorySource.HYPOTHESIS,
            active_state_proof=ActiveStateProof.READY_FOR_EVALUATION,
        ),
        ProvenanceManifestEntry(
            object_type=ManifestObjectType.DATA_PROFILE,
            object_id=bundle.data_profile.data_profile_id,
            version_or_fingerprint=bundle.data_profile.version_fingerprint,
            inclusion_role=InclusionRole.GROUND_TRUTH_PROFILE,
            repository_source=RepositorySource.DATA_PROFILE,
            active_state_proof=ActiveStateProof.ACTIVE_ACCEPTED_GROUND_TRUTH,
        ),
    ]
    entries.extend(
        ProvenanceManifestEntry(
            object_type=ManifestObjectType.ANALYSIS_FRAME,
            object_id=frame.analysis_frame_id,
            version_or_fingerprint=frame.frame_fingerprint,
            inclusion_role=InclusionRole.DATA_SCOPE_PROVENANCE,
            repository_source=RepositorySource.ANALYSIS_FRAME,
            active_state_proof=ActiveStateProof.LINEAGE_VALIDATED,
        )
        for frame in bundle.analysis_frames
    )
    entries.extend(
        ProvenanceManifestEntry(
            object_type=ManifestObjectType.EXECUTION_RUN,
            object_id=run.execution_run_id,
            version_or_fingerprint=run.run_fingerprint,
            inclusion_role=InclusionRole.EXECUTION_PROVENANCE,
            repository_source=RepositorySource.EXECUTION_RUN,
            active_state_proof=ActiveStateProof.EVIDENCE_ADMITTED,
        )
        for run in bundle.execution_runs
    )
    entries.extend(
        ProvenanceManifestEntry(
            object_type=ManifestObjectType.EVIDENCE,
            object_id=evidence.evidence_id,
            version_or_fingerprint=evidence.evidence_fingerprint,
            inclusion_role=InclusionRole.OBSERVED_PREMISE,
            repository_source=RepositorySource.EVIDENCE,
            active_state_proof=ActiveStateProof.ACTIVE_EVIDENCE,
        )
        for evidence in bundle.admitted_evidence
    )
    return BundleProvenanceManifest(bundle_digest=bundle.input_digest, entries=tuple(entries))

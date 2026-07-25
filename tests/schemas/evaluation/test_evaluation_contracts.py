"""Behavior tests for canonical scientific-specialist contracts."""

from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from schemas.common import (
    DiscoveryClaim,
    EvaluationThresholds,
    EvidenceResultSummary,
    MethodParameter,
    ValidityBasis,
)
from schemas.enums import (
    AnalysisIntent,
    DatasetSourceType,
    DiscoveryEpistemicStatus,
    EvidenceType,
)
from schemas.evaluation import (
    AdmittedEvidenceSnapshot,
    AnalysisFrameEvaluationSnapshot,
    DataProfileEvaluationSnapshot,
    DecisionRuleSnapshot,
    DiscoveryProposal,
    DiscoverySynthesisBundle,
    EvaluationFailure,
    EvaluationFailureReason,
    EvidenceResultSnapshot,
    ExecutionRunEvaluationSnapshot,
    HypothesisAnalystResult,
    HypothesisEvaluationSnapshot,
    MethodParameterSnapshot,
)
from schemas.execution.data_explorer import (
    DataExplorerFailureReason,
    DataExplorerResult,
    DataExplorerSuccessResult,
    ExecutionDetails,
    TechnicalDiagnostic,
    TechnicalRetryDisposition,
)
from schemas.execution.observations import AnalysisFrameObservation, EvidenceObservation


def _analysis_frame_observation() -> AnalysisFrameObservation:
    return AnalysisFrameObservation(
        frame_hash="hash123",
        frame_ref="frame:1",
        column_refs=["col_a", "col_b"],
        row_filter_description="x > 0",
    )


def _evidence_observation() -> EvidenceObservation:
    return EvidenceObservation(
        evidence_type=EvidenceType.STATISTICAL_TEST,
        method="pearson_correlation",
        parameters=[MethodParameter(name="alpha", value=0.05)],
        result_summary=EvidenceResultSummary(
            summary="Moderate positive correlation observed.",
            metric_name="p_value",
            metric_value=0.01,
        ),
        artifact_refs=["artifact:result"],
        limitations=["Small sample size"],
        code_reference="git:abc123",
        environment_reference="lock:abc123",
    )


def _data_explorer_payload() -> dict[str, object]:
    return {
        "status": "success",
        "analysis_frame": _analysis_frame_observation().model_dump(mode="python"),
        "evidence_observation": _evidence_observation().model_dump(mode="python"),
        "execution_details": {
            "deterministic_seed": 7,
            "source_sample_size": 120,
            "effective_sample_size": 112,
            "exclusions": ["Eight rows excluded by the approved null policy."],
            "missing_data_policy": "complete cases",
            "technical_limitations": ["Single-process execution"],
        },
        "execution_diagnostics": [{"code": "runtime", "message": "Execution completed in 120 ms."}],
    }


def _bundle() -> DiscoverySynthesisBundle:
    profile_id = uuid4()
    hypothesis_id = uuid4()
    frame_id = uuid4()
    run_id = uuid4()
    evidence_id = uuid4()
    parameters = (MethodParameterSnapshot(name="alpha", value=0.05),)
    evidence = AdmittedEvidenceSnapshot(
        evidence_id=evidence_id,
        hypothesis_id=hypothesis_id,
        data_profile_id=profile_id,
        analysis_frame_id=frame_id,
        execution_run_id=run_id,
        evidence_type=EvidenceType.STATISTICAL_TEST,
        method="pearson_correlation",
        parameters=parameters,
        result=EvidenceResultSnapshot(
            summary="Correlation observed.",
            metric_name="p_value",
            metric_value=0.01,
        ),
        code_reference="git:abc123",
        environment_reference="lock:abc123",
        evidence_fingerprint="e" * 64,
    )
    return DiscoverySynthesisBundle(
        hypothesis=HypothesisEvaluationSnapshot(
            hypothesis_id=hypothesis_id,
            data_profile_id=profile_id,
            statement="Variable X is associated with Variable Y.",
            analysis_intent=AnalysisIntent.CONFIRMATORY,
            variables=("col_a", "col_b"),
            scope="Accepted records in the profiled dataset.",
            validation_method="pearson_correlation",
            method_parameters=parameters,
            decision_rule=DecisionRuleSnapshot(p_value=0.05),
            evidence_expectation="A finite p-value from the approved method.",
        ),
        data_profile=DataProfileEvaluationSnapshot(
            data_profile_id=profile_id,
            source_type=DatasetSourceType.FILE,
            version_fingerprint="d" * 64,
            dvc_hash="dvc:abc123",
            row_count=120,
            column_count=2,
        ),
        analysis_frames=(
            AnalysisFrameEvaluationSnapshot(
                analysis_frame_id=frame_id,
                data_profile_id=profile_id,
                frame_fingerprint="f" * 64,
                frame_hash="hash123",
                frame_ref="frame:1",
                column_refs=("col_a", "col_b"),
            ),
        ),
        execution_runs=(
            ExecutionRunEvaluationSnapshot(
                execution_run_id=run_id,
                task_id=uuid4(),
                hypothesis_id=hypothesis_id,
                analysis_frame_id=frame_id,
                executor_type="deterministic",
                method_id="pearson_correlation",
                parameter_hash="p" * 64,
                attempt_version=1,
                run_fingerprint="r" * 64,
            ),
        ),
        admitted_evidence=(evidence,),
        required_invalidators=(
            "DataProfile, frame, method, parameters, code, and environment must remain stable.",
        ),
        input_digest="b" * 64,
    )


def _validity_basis(evidence_id) -> ValidityBasis:
    return ValidityBasis(
        data_profile_id=uuid4(),
        analysis_frame_refs=["frame:1"],
        hypothesis_id=uuid4(),
        evidence_ids=[evidence_id],
        method="pearson_correlation",
        parameters=[MethodParameter(name="alpha", value=0.05)],
        code_reference="git:abc123",
        environment_reference="lock:abc123",
        decision_rule=EvaluationThresholds(p_value=0.05),
        strength="moderate",
        uncertainty="Sampling uncertainty remains.",
        assumptions_excluded_from_inference=True,
        invalidators=["DataProfile or method identity changes."],
    )


class TestDataExplorerContracts:
    def test_success_and_failure_discrimination_parses_actual_payloads(self) -> None:
        adapter = TypeAdapter(DataExplorerResult)
        success = adapter.validate_python(_data_explorer_payload())
        failure = adapter.validate_python(
            {
                "status": "failed",
                "failure_reason": DataExplorerFailureReason.METHOD_EXECUTION_FAILURE,
                "message": "The approved method failed before producing observations.",
                "retry_disposition": TechnicalRetryDisposition.UNDETERMINED,
            }
        )

        assert isinstance(success, DataExplorerSuccessResult)
        assert failure.status == "failed"
        assert failure.failure_reason is DataExplorerFailureReason.METHOD_EXECUTION_FAILURE

    @pytest.mark.parametrize(
        "forbidden_field",
        [
            "execution_run_id",
            "dispatch_idempotency_key",
            "lease_epoch",
            "task_id",
            "hypothesis_id",
            "data_profile_id",
            "parameter_hash",
            "approved_executor_id",
            "approved_method_id",
            "approved_parameter_hash",
            "approval_state",
            "planner_operation_id",
            "finalize",
            "should_finalize",
            "recommended_decision",
            "scientific_outcome",
            "conclusion",
            "claim",
            "discovery",
            "discovery_proposal",
            "epistemic_status",
            "evaluation",
            "planner_operation",
        ],
    )
    def test_success_rejects_durable_identity_and_scientific_authority(
        self, forbidden_field: str
    ) -> None:
        payload = _data_explorer_payload()
        payload[forbidden_field] = "forbidden"

        with pytest.raises(ValidationError):
            TypeAdapter(DataExplorerResult).validate_python(payload)

    @pytest.mark.parametrize("nested_field", ["finalize", "evaluation", "discovery_claim"])
    def test_nested_observations_reject_hidden_scientific_authority(
        self, nested_field: str
    ) -> None:
        payload = _data_explorer_payload()
        observation = dict(payload["evidence_observation"])
        observation[nested_field] = "forbidden"
        payload["evidence_observation"] = observation

        with pytest.raises(ValidationError):
            TypeAdapter(DataExplorerResult).validate_python(payload)

    def test_typed_execution_details_and_diagnostics_are_bounded(self) -> None:
        payload = _data_explorer_payload()
        details = dict(payload["execution_details"])
        details["context"] = {"task_id": str(uuid4())}
        payload["execution_details"] = details

        with pytest.raises(ValidationError):
            TypeAdapter(DataExplorerResult).validate_python(payload)

        diagnostic = TechnicalDiagnostic(code="runtime", message="Completed.")
        assert diagnostic.model_dump(mode="json") == {
            "code": "runtime",
            "message": "Completed.",
        }

    def test_serialization_is_deterministic_and_round_trips_through_union(self) -> None:
        adapter = TypeAdapter(DataExplorerResult)
        result = adapter.validate_python(_data_explorer_payload())
        first = result.model_dump_json()
        second = result.model_dump_json()
        restored = adapter.validate_json(first)

        assert first == second
        assert restored == result


class TestDiscoverySynthesisBundle:
    def test_bundle_contains_only_typed_scientific_snapshots(self) -> None:
        bundle = _bundle()

        assert bundle.contract_version == "1.0"
        assert bundle.data_profile.accepted_as_ground_truth is True
        assert bundle.hypothesis.validation_method == "pearson_correlation"
        assert bundle.admitted_evidence[0].lifecycle_state == "active"

    @pytest.mark.parametrize(
        "forbidden_field",
        [
            "assumption",
            "task",
            "discovery",
            "session_frame",
            "user_decision",
            "generated_view",
            "raw_chat",
            "pending_work",
            "stale_context",
            "dead_ends",
            "cache_summaries",
            "context",
            "metadata",
        ],
    )
    def test_bundle_rejects_unsafe_context_roles(self, forbidden_field: str) -> None:
        payload = _bundle().model_dump(mode="python")
        payload[forbidden_field] = "forbidden"

        with pytest.raises(ValidationError):
            DiscoverySynthesisBundle.model_validate(payload)

    def test_snapshot_types_reject_nested_task_and_context_state(self) -> None:
        payload = _bundle().model_dump(mode="python")
        hypothesis = dict(payload["hypothesis"])
        hypothesis["task_id"] = uuid4()
        hypothesis["status"] = "completed"
        payload["hypothesis"] = hypothesis

        with pytest.raises(ValidationError):
            DiscoverySynthesisBundle.model_validate(payload)

    def test_bundle_and_nested_snapshots_are_frozen(self) -> None:
        bundle = _bundle()

        with pytest.raises(ValidationError):
            bundle.input_digest = "changed"
        with pytest.raises(ValidationError):
            bundle.hypothesis.scope = "expanded"

    @pytest.mark.parametrize(
        ("mutation", "message"),
        [
            ("profile", "Hypothesis snapshot must match"),
            ("frame", "AnalysisFrame snapshots must match"),
            ("hypothesis", "match the approved Hypothesis contract"),
            ("inactive", "Input should be 'active'"),
            ("frame_ref", "exactly the AnalysisFrames"),
            ("method", "match the approved Hypothesis contract"),
            ("parameters", "match the approved Hypothesis contract"),
        ],
    )
    def test_bundle_rejects_inadmissible_lineage(self, mutation: str, message: str) -> None:
        payload = _bundle().model_dump(mode="python")
        if mutation == "profile":
            payload["hypothesis"]["data_profile_id"] = uuid4()
        elif mutation == "frame":
            payload["analysis_frames"][0]["data_profile_id"] = uuid4()
        else:
            evidence = dict(payload["admitted_evidence"][0])
            if mutation == "hypothesis":
                evidence["hypothesis_id"] = uuid4()
            elif mutation == "inactive":
                evidence["lifecycle_state"] = "superseded"
            elif mutation == "frame_ref":
                evidence["analysis_frame_id"] = uuid4()
            elif mutation == "method":
                evidence["method"] = "different_method"
            elif mutation == "parameters":
                evidence["parameters"] = [{"name": "alpha", "value": 0.01}]
            payload["admitted_evidence"] = [evidence]

        with pytest.raises(ValidationError, match=message):
            DiscoverySynthesisBundle.model_validate(payload)

    def test_serialization_is_deterministic(self) -> None:
        bundle = _bundle()
        assert bundle.model_dump_json() == bundle.model_dump_json()
        assert DiscoverySynthesisBundle.model_validate_json(bundle.model_dump_json()) == bundle


class TestHypothesisAnalystResults:
    @pytest.mark.parametrize(
        ("status", "wording"),
        [
            (DiscoveryEpistemicStatus.SUPPORTED, "Evidence supports the claim within scope."),
            (
                DiscoveryEpistemicStatus.CONTRADICTED,
                "Evidence contradicts the claim within scope.",
            ),
            (
                DiscoveryEpistemicStatus.INCONCLUSIVE,
                "Available evidence is inconclusive for the claim within scope.",
            ),
            (
                DiscoveryEpistemicStatus.INSUFFICIENT_EVIDENCE,
                "Available evidence is insufficient to evaluate the claim within scope.",
            ),
        ],
    )
    def test_all_scientific_outcomes_are_discovery_proposals(
        self, status: DiscoveryEpistemicStatus, wording: str
    ) -> None:
        evidence_id = uuid4()
        proposal = DiscoveryProposal(
            claim=DiscoveryClaim(
                statement=wording,
                scope="Approved scope",
                result="Observed evidence was evaluated within the approved scope.",
            ),
            epistemic_status=status,
            scope="Approved scope",
            evidence_ids=[evidence_id],
            validity_basis=_validity_basis(evidence_id),
        )

        assert proposal.status == "proposed"
        assert proposal.epistemic_status is status

    def test_inadmissible_inputs_are_typed_failures(self) -> None:
        adapter = TypeAdapter(HypothesisAnalystResult)
        for reason in EvaluationFailureReason:
            result = adapter.validate_python(
                {
                    "status": "failed",
                    "failure_reason": reason,
                    "message": "Evaluation cannot proceed.",
                }
            )
            assert isinstance(result, EvaluationFailure)
            assert result.failure_reason is reason

    @pytest.mark.parametrize(
        "forbidden_field",
        [
            "discovery_id",
            "commit",
            "approval_state",
            "finalize",
            "planner_operation",
            "task_status",
            "hypothesis_status",
        ],
    )
    def test_proposal_rejects_persistence_and_lifecycle_authority(
        self, forbidden_field: str
    ) -> None:
        evidence_id = uuid4()
        payload = {
            "status": "proposed",
            "claim": {
                "statement": "Evidence supports the claim.",
                "scope": "Approved scope",
                "result": "Observed evidence supports the scoped claim.",
            },
            "epistemic_status": DiscoveryEpistemicStatus.SUPPORTED,
            "scope": "Approved scope",
            "evidence_ids": [evidence_id],
            "validity_basis": _validity_basis(evidence_id).model_dump(mode="python"),
            forbidden_field: "forbidden",
        }

        with pytest.raises(ValidationError):
            TypeAdapter(HypothesisAnalystResult).validate_python(payload)

    def test_proposal_rejects_scope_and_validity_mismatch(self) -> None:
        evidence_id = uuid4()
        basis = _validity_basis(evidence_id)

        with pytest.raises(ValidationError, match="claim scope must match"):
            DiscoveryProposal(
                claim=DiscoveryClaim(
                    statement="Scoped claim.",
                    scope="Expanded scope",
                    result="Observed result.",
                ),
                epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
                scope="Approved scope",
                evidence_ids=[evidence_id],
                validity_basis=basis,
            )
        with pytest.raises(ValidationError, match="requires evidence strength"):
            DiscoveryProposal(
                claim=DiscoveryClaim(
                    statement="Scoped claim.",
                    scope="Approved scope",
                    result="Observed result.",
                ),
                epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
                scope="Approved scope",
                evidence_ids=[evidence_id],
                validity_basis=basis.model_copy(update={"strength": None}),
            )

    def test_union_rejects_none_plus_error_string(self) -> None:
        with pytest.raises(ValidationError):
            TypeAdapter(HypothesisAnalystResult).validate_python(
                {"status": "failed", "failure_reason": None, "message": "error"}
            )


class TestDependencyAndOwnershipBoundaries:
    def test_observations_have_one_schema_owner(self) -> None:
        assert AnalysisFrameObservation.__module__ == "schemas.execution.observations"
        assert EvidenceObservation.__module__ == "schemas.execution.observations"

    def test_specialist_contract_types_have_no_application_or_framework_owners(self) -> None:
        contract_types = (
            AnalysisFrameEvaluationSnapshot,
            DataProfileEvaluationSnapshot,
            DiscoveryProposal,
            DiscoverySynthesisBundle,
            EvaluationFailure,
            ExecutionDetails,
            HypothesisEvaluationSnapshot,
            TechnicalDiagnostic,
        )
        for contract_type in contract_types:
            assert contract_type.__module__.startswith("schemas.")
            assert not contract_type.__module__.startswith(
                ("application.", "agents.", "langgraph.", "sqlmodel.")
            )

    def test_executor_modules_do_not_import_legacy_executor_result(self) -> None:
        import sys

        for module_name in list(sys.modules.keys()):
            if module_name.startswith("agents.executor.") or module_name == "agents.executor":
                module = sys.modules[module_name]
                if hasattr(module, "ExecutorResult"):
                    # Legacy ExecutorResult must not be imported into executor agent packages
                    raise AssertionError(f"Module {module_name} imports legacy ExecutorResult")

    def test_schemas_do_not_import_application_compatibility(self) -> None:
        import schemas.evaluation

        assert not hasattr(schemas.evaluation, "legacy_scientific_result_bridge")


class TestObservationReceiptEnvelope:
    def test_success_result_maps_to_observation_receipt_envelope(self) -> None:
        from schemas.execution.contracts import (
            ExecutionReceiptEnvelope,
        )
        success = DataExplorerSuccessResult(
            status="success",
            analysis_frame=_analysis_frame_observation(),
            evidence_observation=_evidence_observation().model_copy(
                update={"method": "deterministic_test"}
            ),
        )

        receipt = TypeAdapter(ExecutionReceiptEnvelope).validate_python(
            success.model_dump(mode="json")
        )

        assert isinstance(receipt, DataExplorerSuccessResult)
        assert receipt == success
        assert "execution_run" not in type(receipt).model_fields

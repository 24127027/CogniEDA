"""Package 6 inventory, quarantine, and conservative legacy-state migration."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session, select

from db.models import (
    AnalysisFrameRecord,
    DiscoveryAdmissionClaimRecord,
    DiscoveryRecord,
    EvaluationControlRecord,
    EvidenceRecord,
    ExecutionInboxRecord,
    ExecutionRunRecord,
    HypothesisRecord,
    ProposalDecisionRecord,
    SessionFrameRecord,
    TaskRecord,
)
from schemas.enums import (
    DiscoveryAdmissionClaimState,
    DiscoveryLifecycleState,
    EvaluationControlState,
    EvidenceLifecycleState,
    ExecutionRunStatus,
    HypothesisStatus,
    SessionFrameStatus,
    TaskKind,
    TaskLifecycleState,
    ValiditySourceState,
)

PACKAGE6_MIGRATION_NAME = "package6_legacy_scientific_cutover"
PACKAGE6_MIGRATION_VERSION = 1
_LEGACY_RUN_STATES = {"completed", "finalizing"}
_LEGACY_HYPOTHESIS_STATES = {
    "confirmed",
    "contradicted",
    "inconclusive",
    "insufficient_evidence",
}
_LEGACY_AUTHORITY_KEYS = {
    "evaluation",
    "hypothesis_evaluation",
    "legacy_eval",
    "epistemic_status",
    "finalize",
    "should_finalize",
    "discovery_claim",
    "target_hypothesis_status",
    "target_task_status",
    "execution_run",
}


@dataclass(frozen=True, slots=True)
class LegacyInventoryReport:
    """Complete classification counts for old scientific durable categories."""

    legacy_inbox_payloads_count: int
    legacy_completed_runs_count: int
    legacy_finalizing_runs_count: int
    legacy_terminal_hypotheses_count: int
    quarantined_records_count: int
    pending_legacy_inboxes_count: int = 0
    processed_legacy_inboxes_count: int = 0
    failure_placeholders_count: int = 0
    partial_artifact_chains_count: int = 0
    legacy_session_frames_count: int = 0
    unverified_discoveries_count: int = 0
    details: dict[str, Any] = field(default_factory=dict)


class LegacyPayloadMigrator:
    """Classify every legacy category without inventing scientific meaning."""

    def __init__(self, session: Session) -> None:
        if session.get_bind().dialect.name != "sqlite":
            raise ValueError("Package 6 legacy migration supports SQLite only.")
        self.session = session

    def inventory(self) -> LegacyInventoryReport:
        """Inspect old payloads, states, artifacts, Discoveries, and conclusion frames."""

        self._ensure_control_tables()
        legacy_inboxes: list[ExecutionInboxRecord] = []
        failure_placeholders: list[ExecutionInboxRecord] = []
        for inbox in self.session.exec(select(ExecutionInboxRecord)).all():
            payload = inbox.serialized_observations or {}
            if _payload_has_legacy_authority(payload):
                legacy_inboxes.append(inbox)
            if _is_legacy_failure_placeholder(inbox):
                failure_placeholders.append(inbox)

        runs = self._legacy_run_rows()
        hypotheses = self._legacy_hypothesis_rows()
        partial_runs = [run for run in runs if not self._raw_run_has_exact_observation_chain(run)]
        unverified_discoveries = [
            discovery
            for discovery in self.session.exec(select(DiscoveryRecord)).all()
            if not self._discovery_has_verified_admission(discovery)
        ]
        legacy_frames = [
            frame
            for frame in self.session.exec(select(SessionFrameRecord)).all()
            if self._is_unverified_conclusion_frame(frame)
        ]
        quarantined_count = self.session.exec(
            text("SELECT COUNT(*) FROM legacy_scientific_quarantine")
        ).one()[0]

        return LegacyInventoryReport(
            legacy_inbox_payloads_count=len(legacy_inboxes),
            legacy_completed_runs_count=sum(
                str(run["status"]).lower() == "completed" for run in runs
            ),
            legacy_finalizing_runs_count=sum(
                str(run["status"]).lower() == "finalizing" for run in runs
            ),
            legacy_terminal_hypotheses_count=len(hypotheses),
            quarantined_records_count=quarantined_count,
            pending_legacy_inboxes_count=sum(inbox.status == "pending" for inbox in legacy_inboxes),
            processed_legacy_inboxes_count=sum(
                inbox.status != "pending" for inbox in legacy_inboxes
            ),
            failure_placeholders_count=len(failure_placeholders),
            partial_artifact_chains_count=len(partial_runs),
            legacy_session_frames_count=len(legacy_frames),
            unverified_discoveries_count=len(unverified_discoveries),
            details={
                "legacy_inbox_ids": [str(inbox.inbox_id) for inbox in legacy_inboxes],
                "partial_run_ids": [str(run["execution_run_id"]) for run in partial_runs],
                "unverified_discovery_ids": [
                    str(discovery.discovery_id) for discovery in unverified_discoveries
                ],
                "legacy_session_frame_ids": [
                    str(frame.session_frame_id) for frame in legacy_frames
                ],
            },
        )

    def migrate_all(self) -> dict[str, int]:
        """Run one rollback-safe, idempotent Package 6 migration transaction."""

        self._ensure_control_tables()
        try:
            inboxes = self.migrate_inbox_payloads()
            discoveries = self.quarantine_unverified_discoveries()
            self.session.flush()
            runs = self.migrate_legacy_runs()
            hypotheses = self.migrate_legacy_hypotheses()
            frames = self.quarantine_legacy_session_frames()
            self._record_completed_marker()
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return {
            "inbox_migrated": inboxes,
            "runs_migrated": runs,
            "discoveries_quarantined": discoveries,
            "hypotheses_migrated": hypotheses,
            "session_frames_quarantined": frames,
        }

    def migrate_inbox_payloads(self) -> int:
        """Quarantine legacy payloads in place; never strip or promote their content."""

        migrated = 0
        for inbox in self.session.exec(select(ExecutionInboxRecord)).all():
            if inbox.status == "quarantined":
                continue
            payload = inbox.serialized_observations or {}
            reasons: list[str] = []
            if _payload_has_legacy_authority(payload):
                reasons.append("legacy_scientific_authority_payload")
            if _is_legacy_failure_placeholder(inbox):
                reasons.append("legacy_failure_placeholder")
            if not reasons:
                continue
            self._quarantine(
                "execution_inbox",
                inbox.inbox_id,
                ",".join(reasons),
                {
                    "status": inbox.status,
                    "executor_status": inbox.executor_status,
                    "serialized_observations": payload,
                    "error_message": inbox.error_message,
                },
            )
            inbox.status = "quarantined"
            inbox.processed_at = inbox.processed_at or datetime.now(UTC)
            inbox.error_message = _append_reason(
                inbox.error_message, "QUARANTINED_PACKAGE6_LEGACY_PAYLOAD"
            )
            self.session.flush()
            migrated += 1
        return migrated

    def migrate_legacy_runs(self) -> int:
        """Admit only exact observed artifact chains; quarantine every partial chain."""

        migrated = 0
        runs = self._legacy_run_rows()
        for row in runs:
            run_id = UUID(str(row["execution_run_id"]))
            legacy_status = str(row["status"]).lower()
            if self._raw_run_has_exact_observation_chain(row):
                self.session.execute(
                    text(
                        "UPDATE execution_runs SET status = :status, "
                        "finalization_expires_at = NULL, recovery_status = :recovery_status "
                        "WHERE execution_run_id = :run_id"
                    ),
                    {
                        "status": ExecutionRunStatus.EVIDENCE_ADMITTED.value,
                        "recovery_status": "MIGRATED_PACKAGE6_EXACT_OBSERVATION_CHAIN",
                        "run_id": run_id.hex,
                    },
                )
            else:
                self.session.execute(
                    text(
                        "UPDATE execution_runs SET status = :status, "
                        "validity_state = :validity_state, validity_reason = :validity_reason, "
                        "recovery_status = :recovery_status "
                        "WHERE execution_run_id = :run_id"
                    ),
                    {
                        "status": ExecutionRunStatus.ABANDONED.value,
                        "validity_state": ValiditySourceState.UNVERIFIED.name,
                        "validity_reason": "legacy_partial_scientific_artifact_chain",
                        "recovery_status": "QUARANTINED_PACKAGE6_PARTIAL_CHAIN",
                        "run_id": run_id.hex,
                    },
                )
                self._quarantine(
                    "execution_run",
                    run_id,
                    "legacy_partial_scientific_artifact_chain",
                    {
                        "legacy_status": legacy_status,
                        "analysis_frame_id": (
                            str(row["analysis_frame_id"]) if row["analysis_frame_id"] else None
                        ),
                        "hypothesis_id": (
                            str(row["hypothesis_id"]) if row["hypothesis_id"] else None
                        ),
                    },
                )
            migrated += 1
        self.session.expire_all()
        return migrated

    def quarantine_unverified_discoveries(self) -> int:
        """Invalidate application-authored Discoveries lacking the exact governance chain."""

        changed = 0
        for discovery in self.session.exec(select(DiscoveryRecord)).all():
            if self._discovery_has_verified_admission(discovery):
                continue
            self._quarantine(
                "discovery",
                discovery.discovery_id,
                "legacy_unverified_discovery_authority",
                {
                    "hypothesis_id": str(discovery.hypothesis_id),
                    "evidence_ids": discovery.evidence_ids,
                    "claim": discovery.claim,
                    "epistemic_status": _state_key(discovery.epistemic_status),
                },
            )
            if discovery.lifecycle_state != DiscoveryLifecycleState.INVALIDATED:
                discovery.lifecycle_state = DiscoveryLifecycleState.INVALIDATED
                discovery.review_reasons = _append_unique(
                    discovery.review_reasons, "legacy_unverified_discovery_authority"
                )
                changed += 1
        return changed

    def migrate_legacy_hypotheses(self) -> int:
        """Remove legacy scientific outcomes from Hypothesis without inferring a conclusion."""

        migrated = 0
        hypotheses = self._legacy_hypothesis_rows()
        for row in hypotheses:
            hypothesis_id = UUID(str(row["hypothesis_id"]))
            self.session.execute(
                text("UPDATE hypotheses SET status = :status WHERE hypothesis_id = :hypothesis_id"),
                {
                    "status": HypothesisStatus.ARCHIVED.name,
                    "hypothesis_id": hypothesis_id.hex,
                },
            )
            self.session.expire_all()
            hypothesis = self.session.get(HypothesisRecord, hypothesis_id)
            if hypothesis is None:
                raise ValueError(
                    f"Legacy Hypothesis disappeared during migration: {hypothesis_id}."
                )
            verified_discovery = self._verified_discovery_for_hypothesis(hypothesis.hypothesis_id)
            if verified_discovery is not None:
                hypothesis.status = HypothesisStatus.EVALUATED
            elif self._hypothesis_has_active_exact_evidence(hypothesis.hypothesis_id):
                hypothesis.status = HypothesisStatus.READY_FOR_EVALUATION
                hypothesis.review_reasons = _append_unique(
                    hypothesis.review_reasons, "legacy_terminal_outcome_removed"
                )
                self._reactivate_unverified_completed_task(hypothesis)
            else:
                hypothesis.status = HypothesisStatus.ARCHIVED
                hypothesis.review_reasons = _append_unique(
                    hypothesis.review_reasons,
                    "legacy_terminal_hypothesis_without_admissible_evidence",
                )
                self._reactivate_unverified_completed_task(hypothesis)
            self._quarantine(
                "hypothesis",
                hypothesis.hypothesis_id,
                "legacy_scientific_terminal_status",
                {"replacement_status": _state_key(hypothesis.status)},
            )
            self.session.flush()
            migrated += 1
        return migrated

    def _legacy_run_rows(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.session.execute(
                text(
                    "SELECT execution_run_id, task_id, hypothesis_id, analysis_frame_id, "
                    "method_id, status FROM execution_runs "
                    "WHERE lower(status) IN ('completed', 'finalizing')"
                )
            )
            .mappings()
            .all()
        ]

    def _legacy_hypothesis_rows(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.session.execute(
                text(
                    "SELECT hypothesis_id, status FROM hypotheses "
                    "WHERE lower(status) IN "
                    "('confirmed', 'contradicted', 'inconclusive', "
                    "'insufficient_evidence')"
                )
            )
            .mappings()
            .all()
        ]

    def _raw_run_has_exact_observation_chain(self, run: dict[str, Any]) -> bool:
        if (
            run["analysis_frame_id"] is None
            or run["hypothesis_id"] is None
            or run["task_id"] is None
        ):
            return False
        run_id = UUID(str(run["execution_run_id"]))
        frame_id = UUID(str(run["analysis_frame_id"]))
        hypothesis_id = UUID(str(run["hypothesis_id"]))
        task_id = UUID(str(run["task_id"]))
        frame = self.session.get(AnalysisFrameRecord, frame_id)
        hypothesis = (
            self.session.execute(
                text(
                    "SELECT task_id, profile_id FROM hypotheses "
                    "WHERE hypothesis_id = :hypothesis_id"
                ),
                {"hypothesis_id": hypothesis_id.hex},
            )
            .mappings()
            .one_or_none()
        )
        task_exists = self.session.execute(
            text("SELECT 1 FROM tasks WHERE task_id = :task_id"),
            {"task_id": task_id.hex},
        ).one_or_none()
        if (
            frame is None
            or hypothesis is None
            or task_exists is None
            or UUID(str(hypothesis["task_id"])) != task_id
            or frame.data_profile_id != UUID(str(hypothesis["profile_id"]))
        ):
            return False
        evidence_rows = self.session.exec(
            select(EvidenceRecord).where(EvidenceRecord.execution_run_ref == str(run_id))
        ).all()
        if len(evidence_rows) != 1:
            return False
        evidence = evidence_rows[0]
        return (
            evidence.analysis_frame_ref == str(frame_id)
            and evidence.hypothesis_id == hypothesis_id
            and evidence.profile_id == UUID(str(hypothesis["profile_id"]))
            and evidence.lifecycle_state == EvidenceLifecycleState.ACTIVE
            and evidence.method == run["method_id"]
        )

    def quarantine_legacy_session_frames(self) -> int:
        """Exclude conclusion frames not proven by a committed admission claim."""

        changed = 0
        for frame in self.session.exec(select(SessionFrameRecord)).all():
            if not self._is_unverified_conclusion_frame(frame):
                continue
            self._quarantine(
                "session_frame",
                frame.session_frame_id,
                "legacy_unverified_conclusion_frame",
                {
                    "frame_outcome": frame.frame_outcome,
                    "relevant_discovery_refs": frame.relevant_discovery_refs,
                },
            )
            if frame.frame_status != SessionFrameStatus.SUPERSEDED:
                frame.frame_status = SessionFrameStatus.SUPERSEDED
                marker = {
                    "artifact_type": "session_frame",
                    "reason": "legacy_unverified_conclusion_frame",
                    "ref_id": str(frame.session_frame_id),
                    "replacement_ref_id": None,
                }
                frame.stale_context = list(frame.stale_context or [])
                if marker not in frame.stale_context:
                    frame.stale_context.append(marker)
                changed += 1
        return changed

    def _has_exact_observation_chain(self, run: ExecutionRunRecord) -> bool:
        if run.analysis_frame_id is None or run.hypothesis_id is None or run.task_id is None:
            return False
        frame = self.session.get(AnalysisFrameRecord, run.analysis_frame_id)
        hypothesis = self.session.get(HypothesisRecord, run.hypothesis_id)
        task = self.session.get(TaskRecord, run.task_id)
        if (
            frame is None
            or hypothesis is None
            or task is None
            or hypothesis.task_id != task.task_id
            or frame.data_profile_id != hypothesis.profile_id
        ):
            return False
        evidence_rows = self.session.exec(
            select(EvidenceRecord).where(
                EvidenceRecord.execution_run_ref == str(run.execution_run_id)
            )
        ).all()
        if len(evidence_rows) != 1:
            return False
        evidence = evidence_rows[0]
        return (
            evidence.execution_run_ref == str(run.execution_run_id)
            and evidence.analysis_frame_ref == str(frame.analysis_frame_id)
            and evidence.hypothesis_id == hypothesis.hypothesis_id
            and evidence.profile_id == hypothesis.profile_id
            and evidence.lifecycle_state == EvidenceLifecycleState.ACTIVE
            and evidence.method == run.method_id
        )

    def _hypothesis_has_active_exact_evidence(self, hypothesis_id: UUID) -> bool:
        evidences = self.session.exec(
            select(EvidenceRecord).where(
                EvidenceRecord.hypothesis_id == hypothesis_id,
                EvidenceRecord.lifecycle_state == EvidenceLifecycleState.ACTIVE,
            )
        ).all()
        if not evidences:
            return False
        for evidence in evidences:
            try:
                execution_run_id = UUID(evidence.execution_run_ref)
            except ValueError:
                return False
            run = self.session.get(ExecutionRunRecord, execution_run_id)
            if run is None or not self._has_exact_observation_chain(run):
                return False
        return True

    def _verified_discovery_for_hypothesis(self, hypothesis_id: UUID) -> DiscoveryRecord | None:
        discoveries = self.session.exec(
            select(DiscoveryRecord).where(DiscoveryRecord.hypothesis_id == hypothesis_id)
        ).all()
        verified = [
            discovery
            for discovery in discoveries
            if self._discovery_has_verified_admission(discovery)
        ]
        return verified[0] if len(verified) == 1 else None

    def _discovery_has_verified_admission(self, discovery: DiscoveryRecord) -> bool:
        claim = self.session.exec(
            select(DiscoveryAdmissionClaimRecord).where(
                DiscoveryAdmissionClaimRecord.discovery_id == discovery.discovery_id,
                DiscoveryAdmissionClaimRecord.state == DiscoveryAdmissionClaimState.COMMITTED,
            )
        ).one_or_none()
        if claim is None or claim.session_frame_id is None:
            return False
        evaluation = self.session.get(EvaluationControlRecord, claim.evaluation_id)
        decision = self.session.get(ProposalDecisionRecord, claim.decision_id)
        frame = self.session.get(SessionFrameRecord, claim.session_frame_id)
        return (
            evaluation is not None
            and evaluation.hypothesis_id == discovery.hypothesis_id
            and evaluation.state == EvaluationControlState.COMMITTED
            and decision is not None
            and decision.hypothesis_id == discovery.hypothesis_id
            and decision.consumed
            and decision.consumed_by == str(discovery.discovery_id)
            and frame is not None
            and str(discovery.discovery_id) in frame.relevant_discovery_refs
        )

    def _is_unverified_conclusion_frame(self, frame: SessionFrameRecord) -> bool:
        if frame.frame_outcome is None or not frame.relevant_discovery_refs:
            return False
        claim = self.session.exec(
            select(DiscoveryAdmissionClaimRecord).where(
                DiscoveryAdmissionClaimRecord.session_frame_id == frame.session_frame_id,
                DiscoveryAdmissionClaimRecord.state == DiscoveryAdmissionClaimState.COMMITTED,
            )
        ).one_or_none()
        return claim is None

    def _reactivate_unverified_completed_task(self, hypothesis: HypothesisRecord) -> None:
        task = self.session.get(TaskRecord, hypothesis.task_id)
        if (
            task is not None
            and task.task_kind == TaskKind.ANALYTICAL
            and task.lifecycle_state == TaskLifecycleState.COMPLETED
        ):
            task.lifecycle_state = TaskLifecycleState.ACTIVE
            task.review_reasons = _append_unique(
                task.review_reasons, "legacy_unverified_scientific_completion"
            )

    def _quarantine(
        self,
        source_type: str,
        source_id: UUID,
        reason: str,
        payload: dict[str, Any],
    ) -> None:
        self.session.exec(
            text(
                "INSERT OR IGNORE INTO legacy_scientific_quarantine "
                "(source_type, source_id, reason, payload_json, quarantined_at) "
                "VALUES (:source_type, :source_id, :reason, :payload_json, :quarantined_at)"
            ),
            params={
                "source_type": source_type,
                "source_id": str(source_id),
                "reason": reason,
                "payload_json": json.dumps(payload, sort_keys=True, default=str),
                "quarantined_at": datetime.now(UTC).isoformat(),
            },
        )

    def _ensure_control_tables(self) -> None:
        self.session.exec(
            text(
                "CREATE TABLE IF NOT EXISTS legacy_scientific_quarantine ("
                "quarantine_id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "source_type TEXT NOT NULL, source_id TEXT NOT NULL, reason TEXT NOT NULL, "
                "payload_json TEXT NOT NULL, quarantined_at TEXT NOT NULL, "
                "UNIQUE(source_type, source_id))"
            )
        )
        self.session.exec(
            text(
                "CREATE TABLE IF NOT EXISTS schema_migration_markers ("
                "migration_name TEXT PRIMARY KEY, version INTEGER NOT NULL, "
                "completed_at TEXT NOT NULL)"
            )
        )
        self.session.exec(
            text(
                "CREATE TRIGGER IF NOT EXISTS legacy_scientific_quarantine_immutable_update "
                "BEFORE UPDATE ON legacy_scientific_quarantine BEGIN "
                "SELECT RAISE(ABORT, 'legacy scientific quarantine is immutable'); END"
            )
        )
        self.session.exec(
            text(
                "CREATE TRIGGER IF NOT EXISTS legacy_scientific_quarantine_immutable_delete "
                "BEFORE DELETE ON legacy_scientific_quarantine BEGIN "
                "SELECT RAISE(ABORT, 'legacy scientific quarantine is immutable'); END"
            )
        )

    def _record_completed_marker(self) -> None:
        existing = self.session.exec(
            text(
                "SELECT version FROM schema_migration_markers "
                "WHERE migration_name = :migration_name"
            ),
            params={"migration_name": PACKAGE6_MIGRATION_NAME},
        ).first()
        if existing is not None and existing[0] != PACKAGE6_MIGRATION_VERSION:
            raise ValueError("Package 6 migration marker has an unsupported version.")
        self.session.exec(
            text(
                "INSERT INTO schema_migration_markers "
                "(migration_name, version, completed_at) "
                "VALUES (:migration_name, :version, :completed_at) "
                "ON CONFLICT(migration_name) DO UPDATE SET "
                "version = excluded.version, completed_at = excluded.completed_at"
            ),
            params={
                "migration_name": PACKAGE6_MIGRATION_NAME,
                "version": PACKAGE6_MIGRATION_VERSION,
                "completed_at": datetime.now(UTC).isoformat(),
            },
        )


def _state_key(value: object) -> str:
    raw = getattr(value, "value", value)
    return str(raw).lower()


def _payload_has_legacy_authority(value: object) -> bool:
    if isinstance(value, dict):
        if _LEGACY_AUTHORITY_KEYS.intersection(value):
            return True
        if value.get("status") == "completed":
            return True
        return any(_payload_has_legacy_authority(item) for item in value.values())
    if isinstance(value, list):
        return any(_payload_has_legacy_authority(item) for item in value)
    return False


def _is_legacy_failure_placeholder(inbox: ExecutionInboxRecord) -> bool:
    if inbox.executor_status != "failed":
        return False
    payload = inbox.serialized_observations or {}
    return (
        payload.get("status") != "failed"
        or not payload.get("failure_reason")
        or not payload.get("message")
        or "analysis_frame" in payload
        or "evidence_observation" in payload
    )


def _append_unique(values: list[str] | None, value: str) -> list[str]:
    result = list(values or [])
    if value not in result:
        result.append(value)
    return result


def _append_reason(existing: str | None, value: str) -> str:
    if not existing:
        return value
    if value in existing:
        return existing
    return f"{existing}; {value}"

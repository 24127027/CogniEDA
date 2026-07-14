"""Deterministic reconciliation of in-flight execution attempts."""

from sqlmodel import Session

from application.orchestrator.reconciler import reconcile_execution_attempts


class ExecutionReconciler:
    def __init__(self, session: Session):
        self._session = session

    def reconcile_all(self) -> None:
        """Delegate to the guarded application reconciler; no direct row writes."""
        reconcile_execution_attempts(self._session)

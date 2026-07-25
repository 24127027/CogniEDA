"""Application execution bounded context."""

from importlib import import_module
from typing import Any

from application.execution.admission import (
    build_execution_admission_operations,
)
from application.execution.cancellation import (
    authorize_retry,
    cancel_execution_attempt,
)
from application.execution.dispatch import (
    DataExplorerDispatcherProtocol,
    dispatch_pending_attempts,
)
from application.execution.identity import (
    canonical_json_bytes,
    canonical_sha256,
    method_parameter_hash,
    result_payload_digest,
)
from application.execution.receiver import (
    submit_execution_result,
)
from application.execution.transition_service import (
    AlreadyCompletedError,
    AlreadyFinalizingError,
    ClaimLostError,
    ExecutionAttemptTransitionService,
    ExecutionTransitionError,
)

_RECOVERY_EXPORTS = {
    "ExecutionReconciliationError",
    "finalize_attempt",
    "reconcile_execution_attempts",
}

__all__ = [
    "AlreadyCompletedError",
    "AlreadyFinalizingError",
    "ClaimLostError",
    "DataExplorerDispatcherProtocol",
    "ExecutionAttemptTransitionService",
    "ExecutionReconciliationError",
    "ExecutionTransitionError",
    "authorize_retry",
    "build_execution_admission_operations",
    "cancel_execution_attempt",
    "canonical_json_bytes",
    "canonical_sha256",
    "dispatch_pending_attempts",
    "finalize_attempt",
    "method_parameter_hash",
    "reconcile_execution_attempts",
    "result_payload_digest",
    "submit_execution_result",
]


def __getattr__(name: str) -> Any:
    """Load recovery exports lazily so Evidence admission can import identity safely."""

    if name not in _RECOVERY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module("application.execution.recovery"), name)
    globals()[name] = value
    return value

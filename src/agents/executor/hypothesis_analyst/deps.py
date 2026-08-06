from __future__ import annotations

from collections.abc import Callable

from schemas.artifacts import Discovery

from ..types import ExecutionRequest, ExecutionResult

DispatcherCall = Callable[[ExecutionRequest], ExecutionResult]
AdmissionCall = Callable[[Discovery], bool]

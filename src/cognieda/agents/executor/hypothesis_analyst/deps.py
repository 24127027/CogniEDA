from __future__ import annotations

from collections.abc import Callable

from cognieda.schemas.artifacts import Discovery

from ..data_explorer.types import DataExplorerResult
from ..types import ExecutionRequest

DispatcherCall = Callable[[ExecutionRequest], DataExplorerResult]
AdmissionCall = Callable[[Discovery], bool]

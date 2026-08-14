from __future__ import annotations

from collections.abc import Callable

from cognieda.agents.data_explorer.contracts import DataExplorerResult
from cognieda.delegation import ExecutionRequest
from cognieda.schemas.artifacts import Discovery

DispatcherCall = Callable[[ExecutionRequest], DataExplorerResult]
AdmissionCall = Callable[[Discovery], bool]

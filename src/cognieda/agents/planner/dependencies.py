from dataclasses import dataclass, field

from cognieda.application.ports import ExecutorDispatcherPort
from cognieda.execution import ExecutionResult, ExecutorContext
from cognieda.schemas.artifacts import DataProfile, Task


@dataclass
class PlannerDeps:
    dispatcher: ExecutorDispatcherPort
    active_task: Task | None = None
    data_profile: DataProfile | None = None
    execution_context: ExecutorContext = field(default_factory=ExecutorContext)
    dataset_digest: str | None = None
    data_results: list[ExecutionResult] = field(default_factory=list)

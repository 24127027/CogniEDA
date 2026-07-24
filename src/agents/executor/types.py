from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from application.orchestrator.execution_contracts import ExecutionSpecification, HypothesisDraft


class DataExplorerInput(BaseModel):
    """Input contract for Data Explorer execution, containing the analytical request."""

    model_config = ConfigDict(extra="forbid")

    execution_run_id: UUID
    task_id: UUID
    hypothesis_id: UUID
    data_profile_id: UUID
    dataset_path: str
    hypothesis: HypothesisDraft
    specification: ExecutionSpecification
    deterministic_seed: int | None = None


class DataExplorerExecutionContext(BaseModel):
    """Operational context seam for Data Explorer execution."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    # Runtime dependencies will be added here (e.g., logger, artifact paths).
    pass

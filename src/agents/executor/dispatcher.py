from __future__ import annotations

from uuid import UUID

from application.orchestrator.execution_contracts import ExecutorResult, PreparedExecution

from .registry import ExecutorRegistry
from .types import ExecutorContext, ExecutorInput


class ExecutorDispatcher:
    def __init__(self, registry: ExecutorRegistry) -> None:
        self._registry = registry

    async def dispatch(
        self, prepared: PreparedExecution, context: ExecutorContext
    ) -> ExecutorResult:
        if prepared.execution_run_id is None:
            raise ValueError("Durable executor dispatch requires an ExecutionRun identity.")
        if prepared.dispatch_idempotency_key is None or prepared.lease_epoch is None:
            raise ValueError("Durable executor dispatch requires attempt fencing identity.")
        if prepared.hypothesis_ref is None:
            raise ValueError("Durable executor dispatch requires a Hypothesis identity.")

        executor = self._registry.get(prepared.specification.executor_id)

        input_data = ExecutorInput(
            execution_run_id=prepared.execution_run_id,
            task_id=_durable_id(prepared.task_ref, "Task"),
            hypothesis_id=_durable_id(prepared.hypothesis_ref, "Hypothesis"),
            data_profile_id=_durable_id(prepared.data_profile_ref, "DataProfile"),
            dataset_path=prepared.dataset_path,
            hypothesis=prepared.hypothesis,
            specification=prepared.specification,
            deterministic_seed=prepared.deterministic_seed,
        )

        return await executor.run(
            input=input_data,
            context=context,
        )


def _durable_id(value: str, label: str) -> UUID:
    try:
        return UUID(value)
    except ValueError as exc:
        raise ValueError(f"Durable executor dispatch requires a canonical {label} UUID.") from exc

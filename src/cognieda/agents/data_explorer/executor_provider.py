"""Data Explorer Executor Provider — ExecutorProvider contract adapter.

This module bridges the Data Explorer's internal workflow (DataExplorer.run())
with the execution dispatcher's ExecutorProvider protocol.

Design:
- DEExecutorProvider wraps DataExplorer and exposes the standard run() interface.
- It accepts ExecutionRequest (and optionally DEExecutorContext for MVP RAM objects).
- It maps ExecutionRequest fields into DEInput and calls DataExplorer.run().
- On success, it stores the emitted Evidence or DataProfile as live RAM pointers
  inside ExecutionResult.emitted_artifacts under the keys "evidence" or
  "data_profile" respectively.

MVP RAM contract:
- Callers that can supply a live DataFrame and DataProfile object should pass a
  DEExecutorContext (subclass of ExecutorContext) in request.context.  This
  bypasses disk I/O for the MVP where there is no persistence layer.
- If context is a plain ExecutorContext, dataset_path is used to read the
  DataFrame from disk (CSV and Parquet supported).

Capability mapping:
- Capability.DATA_PROFILING  -> profiling pass (data_profile=None in DEInput)
- Capability.DATA_ANALYSIS   -> analysis pass (data_profile must be provided in context)
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import UUID, uuid4

import pandas as pd

from cognieda.agents.data_explorer.agent import DataExplorer
from cognieda.agents.data_explorer.context import DEInput
from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.execution.capabilities import Capability
from cognieda.execution.contracts import (
    DEExecutorContext,
    ExecutionFailure,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
)


_SOURCE_ROLE = "data_explorer"


class DEExecutorProvider:
    """ExecutorProvider adapter for the Data Explorer.

    Implements the ExecutorProvider protocol so the DE can be registered with
    the ExecutorRegistry and dispatched by the Planner via the dispatcher.

    Usage:
        provider = DEExecutorProvider(agent_factory=factory, model_config=cfg)
        result = await provider.run(request)
        evidence = result.emitted_artifacts.get("evidence")
        data_profile = result.emitted_artifacts.get("data_profile")
    """

    def __init__(
        self,
        *,
        agent_factory: AgentFactoryPort,
        model_config: ModelConfig,
        max_iterations: int = 3,
    ) -> None:
        self._de = DataExplorer(
            agent_factory=agent_factory,
            model_config=model_config,
            max_iterations=max_iterations,
        )

    async def run(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute a DATA_PROFILING or DATA_ANALYSIS request.

        Extracts dataset and profile from the request context, delegates to
        DataExplorer.run(), and maps the output to a standard ExecutionResult.
        """
        work_id = str(uuid4())
        task_id: UUID = request.input.task.task_id
        capability: Capability = request.capability

        # ------------------------------------------------------------------ #
        # Resolve dataset                                                      #
        # ------------------------------------------------------------------ #
        context = request.context
        is_de_context = isinstance(context, DEExecutorContext)

        df: pd.DataFrame | None = None
        dataset_path: str | None = context.dataset_path
        dataset_digest: str = ""

        if is_de_context and context.dataframe is not None:
            # Caller supplied a live DataFrame — use it directly (MVP path).
            df = context.dataframe
            if dataset_path:
                # Compute digest from path bytes if available.
                try:
                    dataset_digest = hashlib.sha256(
                        Path(dataset_path).read_bytes()
                    ).hexdigest()
                except Exception:  # noqa: BLE001
                    dataset_digest = hashlib.sha256(str(dataset_path).encode()).hexdigest()
            else:
                dataset_digest = hashlib.sha256(str(id(df)).encode()).hexdigest()
                dataset_path = "<in-memory>"
        elif dataset_path:
            # Read from disk.
            p = Path(dataset_path)
            if not p.exists():
                return self._fail(
                    task_id=task_id,
                    work_id=work_id,
                    code="invalid_input",
                    message=f"Dataset file not found: {dataset_path}",
                )
            try:
                if p.suffix == ".csv":
                    df = pd.read_csv(p)
                elif p.suffix == ".parquet":
                    df = pd.read_parquet(p)
                else:
                    return self._fail(
                        task_id=task_id,
                        work_id=work_id,
                        code="invalid_input",
                        message=f"Unsupported file type '{p.suffix}'. Use .csv or .parquet.",
                    )
                dataset_digest = hashlib.sha256(p.read_bytes()).hexdigest()
            except Exception as exc:  # noqa: BLE001
                return self._fail(
                    task_id=task_id,
                    work_id=work_id,
                    code="invalid_input",
                    message=f"Failed to read dataset: {exc}",
                )
        else:
            return self._fail(
                task_id=task_id,
                work_id=work_id,
                code="invalid_input",
                message="ExecutionRequest context must supply dataset_path or a DEExecutorContext with dataframe.",
            )

        # ------------------------------------------------------------------ #
        # Resolve DataProfile for analysis requests                            #
        # ------------------------------------------------------------------ #
        data_profile = None
        if capability == Capability.DATA_ANALYSIS:
            if is_de_context and context.data_profile is not None:
                data_profile = context.data_profile
            else:
                return self._fail(
                    task_id=task_id,
                    work_id=work_id,
                    code="invalid_input",
                    message=(
                        "DATA_ANALYSIS capability requires a DataProfile in DEExecutorContext.data_profile. "
                        "Run DATA_PROFILING first to generate one."
                    ),
                )

        # ------------------------------------------------------------------ #
        # Build DEInput and run                                                #
        # ------------------------------------------------------------------ #
        task_instruction = request.input.task.instruction
        if capability == Capability.DATA_PROFILING:
            task_instruction = "Profile the dataset"

        de_input = DEInput(
            task_instruction=task_instruction,
            dataset_path=str(dataset_path),
            dataset_digest=dataset_digest,
            data_profile=data_profile,
            dataframe=df,
        )

        try:
            output = await self._de.run(task_id, de_input)
        except Exception as exc:  # noqa: BLE001
            return self._fail(
                task_id=task_id,
                work_id=work_id,
                code="execution_failed",
                message=f"Data Explorer raised an unexpected error: {exc}",
            )

        # ------------------------------------------------------------------ #
        # Map DataExplorerOutput -> ExecutionResult                            #
        # ------------------------------------------------------------------ #
        if output.error is not None:
            status = (
                ExecutionStatus.BLOCKED
                if output.error.code.value == "unfeasible_request"
                else ExecutionStatus.FAILED
            )
            return ExecutionResult(
                source_role=_SOURCE_ROLE,
                task_id=task_id,
                work_id=work_id,
                status=status,
                failure=ExecutionFailure(
                    code=output.error.code.value,
                    message=output.error.message,
                ),
            )

        # Success — store artifacts as live RAM pointers.
        emitted: dict[str, object] = {}
        if output.evidence is not None:
            emitted["evidence"] = output.evidence
        if output.data_profile is not None:
            emitted["data_profile"] = output.data_profile

        return ExecutionResult(
            source_role=_SOURCE_ROLE,
            task_id=task_id,
            work_id=work_id,
            status=ExecutionStatus.SUCCEEDED,
            emitted_artifacts=emitted,
        )

    # ---------------------------------------------------------------------- #
    # Helpers                                                                  #
    # ---------------------------------------------------------------------- #

    @staticmethod
    def _fail(
        *,
        task_id: UUID,
        work_id: str,
        code: str,
        message: str,
    ) -> ExecutionResult:
        return ExecutionResult(
            source_role=_SOURCE_ROLE,
            task_id=task_id,
            work_id=work_id,
            status=ExecutionStatus.FAILED,
            failure=ExecutionFailure(code=code, message=message),
        )


__all__ = ("DEExecutorProvider",)

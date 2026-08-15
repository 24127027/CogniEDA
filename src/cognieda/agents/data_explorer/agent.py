"""Data Explorer agent — contract-native executor with LangGraph internal workflow.

Public API
----------
DataExplorer
    .run(request: ExecutionRequest) -> DataExplorerResult
        The ExecutorProvider contract entry point.
    .profile_candidate(dataset_path: str) -> DataProfileCandidate
        Deterministic, no-LLM profiling of a dataset file.

Internal workflow (LangGraph graph)
------------------------------------
The graph: start -> planning -> execute -> check_result -> end
check_result can loop back to planning when execution output is incomplete.

The graph is used when no analysis_planner is injected. When analysis_planner
is supplied (typically in tests), DataExplorer.run() bypasses the graph and
calls the planner directly, producing a deterministic result.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pandas as pd

from cognieda.delegation import (
    Capability,
    ExecutionFailure,
    ExecutionRequest,
    ExecutionStatus,
)
from cognieda.schemas.enums import TaskKind

from .contracts import (
    DataAnalysisPlan,
    DataAnalysisPlannerPort,
    DataAnalysisPlanningRequest,
    DataExplorerInput,
    DataExplorerObservation,
    DataExplorerResult,
    DataExecutionProvenance,
    DataProfileCandidate,
)
from .planning import UnsupportedAnalysisRequest
from .tools import (
    ColumnNotFoundError,
    DataToolError,
    InvalidToolResultError,
    compute_dataset_digest,
    execute_analysis as _tools_execute_analysis,
    normalize_json_value,
    profile_dataframe_to_dict,
    tool_reference,
)

_SOURCE_ROLE = "data_explorer"


# ---------------------------------------------------------------------------
# Module-level execute_analysis — exposed for monkeypatching in tests.
# Tests patch: cognieda.agents.data_explorer.agent.execute_analysis
# _run_analysis references this name via globals(), so the patch takes effect.
# ---------------------------------------------------------------------------

execute_analysis = _tools_execute_analysis


class DataExplorer:
    """Contract-native Data Explorer executor.

    Can be instantiated without any arguments for zero-dep profiling.
    Inject ``analysis_planner`` to override the default LLM-backed planner.

    CAPABILITIES class attribute satisfies the ExecutorProvider protocol checked
    by ExecutorRegistry.register() and ExecutorRegistry.register_provider().
    """

    CAPABILITIES: tuple[Capability, ...] = (
        Capability.DATA_ANALYSIS,
        Capability.DATA_PROFILING,
        Capability.DATA_TRANSFORMATION,
    )

    def __init__(
        self,
        *,
        analysis_planner: DataAnalysisPlannerPort | None = None,
        config: Any | None = None,
        agent_factory: Any | None = None,
        de_model: Any | None = None,
    ) -> None:
        self._analysis_planner = analysis_planner
        self._config = config
        self._agent_factory = agent_factory
        self._de_model = de_model

    # -----------------------------------------------------------------------
    # Public: non-LLM profiling (usable without any model)
    # -----------------------------------------------------------------------

    def profile_candidate(self, dataset_path: str) -> DataProfileCandidate:
        """Profile a dataset file and return a DataProfileCandidate with full provenance.

        The candidate carries no task lineage — it is an initial, non-authoritative
        profile used by the Planner to bind a DataProfile to a Task.
        """
        resolved = _resolve_absolute_path(dataset_path)
        df = _load_df(resolved)
        profile = profile_dataframe_to_dict(df)
        digest = compute_dataset_digest(resolved)
        work_id = f"de:{uuid4()}"
        provenance = DataExecutionProvenance(
            dataset_reference=resolved,
            dataset_digest=digest,
            data_profile_id=None,
            tool_reference=tool_reference("dataset_profile"),
            operation="dataset_profile",
            parameters={"mode": "candidate"},
        )
        return DataProfileCandidate(
            work_id=work_id,
            profile=profile,
            provenance=provenance,
        )

    # -----------------------------------------------------------------------
    # Public: ExecutorProvider contract — `run` is the only authorised entry
    # -----------------------------------------------------------------------

    async def run(self, request: ExecutionRequest) -> DataExplorerResult:
        """Execute a DATA_PROFILING, DATA_ANALYSIS, or DATA_TRANSFORMATION request.

        Returns a DataExplorerResult. Never raises — all failures are encoded in
        the result with ExecutionStatus.FAILED or ExecutionStatus.BLOCKED.
        """
        capability = request.capability
        work_id = f"de:{uuid4()}"
        task_id: UUID = request.input.task.task_id

        # DATA_TRANSFORMATION is not yet implemented.
        if capability is Capability.DATA_TRANSFORMATION:
            return self._blocked(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="successor_data_profile_not_implemented",
                message=(
                    "DATA_TRANSFORMATION is not implemented. "
                    "A successor DataProfile path is required."
                ),
            )

        # Guard: only DATA tasks are accepted for analysis / profiling.
        if capability is Capability.DATA_ANALYSIS:
            if request.input.task.kind is not TaskKind.DATA:
                return self._failed(
                    capability=capability,
                    work_id=work_id,
                    task_id=task_id,
                    code="unsupported_task_kind",
                    message=(
                        f"Data Explorer only accepts DATA tasks; "
                        f"received {request.input.task.kind!r}."
                    ),
                )

        # Resolve the dataset path (must be absolute; no env-var fallback).
        raw_path = request.context.dataset_path
        try:
            dataset_path = _require_absolute_path(raw_path)
        except _InvalidDatasetBinding as exc:
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="invalid_dataset_binding",
                message=str(exc),
            )

        # ------------------------------------------------------------------ #
        # DATA_PROFILING path                                                  #
        # ------------------------------------------------------------------ #
        if capability is Capability.DATA_PROFILING:
            return await self._run_profiling(
                request=request,
                dataset_path=dataset_path,
                work_id=work_id,
                task_id=task_id,
            )

        # ------------------------------------------------------------------ #
        # DATA_ANALYSIS path                                                   #
        # ------------------------------------------------------------------ #
        return await self._run_analysis(
            request=request,
            dataset_path=dataset_path,
            work_id=work_id,
            task_id=task_id,
        )

    # -----------------------------------------------------------------------
    # Private: profiling execution
    # -----------------------------------------------------------------------

    async def _run_profiling(
        self,
        *,
        request: ExecutionRequest,
        dataset_path: str,
        work_id: str,
        task_id: UUID,
    ) -> DataExplorerResult:
        """Execute a DATA_PROFILING request."""
        capability = Capability.DATA_PROFILING
        data_profile_id = request.context.data_profile_id

        # Load dataset.
        try:
            df = _load_df(dataset_path)
        except FileNotFoundError:
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="dataset_not_found",
                message=f"Dataset file not found: {dataset_path}",
            )
        except Exception as exc:  # noqa: BLE001
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="dataset_not_found",
                message=f"Failed to load dataset: {exc}",
            )

        digest = compute_dataset_digest(dataset_path)
        provenance = DataExecutionProvenance(
            dataset_reference=dataset_path,
            dataset_digest=digest,
            data_profile_id=data_profile_id,
            tool_reference=tool_reference("dataset_profile"),
            operation="dataset_profile",
            parameters={"mode": "candidate" if data_profile_id is None else "refresh"},
        )

        # If a data_profile_id is bound, return a profile-refresh observation.
        if data_profile_id is not None:
            profile = profile_dataframe_to_dict(df)
            payload = {"row_count": profile.row_count}
            obs = DataExplorerObservation(
                observation_type="profiling_refresh",
                summary=f"Dataset has {profile.row_count} rows.",
                payload=payload,
            )
            return DataExplorerResult(
                source_role=_SOURCE_ROLE,
                task_id=task_id,
                work_id=work_id,
                status=ExecutionStatus.SUCCEEDED,
                capability=capability,
                observations=[obs],
                produced_data_profile=None,
                provenance=provenance,
            )

        # Initial profiling — produce a candidate DataProfile.
        candidate = self.profile_candidate(dataset_path)
        return DataExplorerResult(
            source_role=_SOURCE_ROLE,
            task_id=task_id,
            work_id=work_id,
            status=ExecutionStatus.SUCCEEDED,
            capability=capability,
            observations=[],
            produced_data_profile=candidate.profile,
            provenance=candidate.provenance,
        )

    # -----------------------------------------------------------------------
    # Private: analysis execution
    # -----------------------------------------------------------------------

    async def _run_analysis(
        self,
        *,
        request: ExecutionRequest,
        dataset_path: str,
        work_id: str,
        task_id: UUID,
    ) -> DataExplorerResult:
        """Execute a DATA_ANALYSIS request."""
        capability = Capability.DATA_ANALYSIS
        data_profile_id = request.context.data_profile_id

        # Extract DataProfile — must be present in DataExplorerInput.
        if not isinstance(request.input, DataExplorerInput):
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="missing_data_profile_binding",
                message=(
                    "DATA_ANALYSIS requires a DataExplorerInput with a bound DataProfile. "
                    "Run DATA_PROFILING first."
                ),
            )
        data_profile = request.input.data_profile

        # Load dataset.
        try:
            df = _load_df(dataset_path)
        except FileNotFoundError:
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="dataset_not_found",
                message=f"Dataset file not found: {dataset_path}",
            )
        except Exception as exc:  # noqa: BLE001
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="dataset_not_found",
                message=f"Failed to load dataset: {exc}",
            )

        # Invoke the analysis planner if provided (fast deterministic test path).
        planner = self._analysis_planner
        if planner is not None:
            return await self._run_analysis_deterministic(
                request=request,
                planner=planner,
                dataset_path=dataset_path,
                data_profile=data_profile,
                data_profile_id=data_profile_id,
                df=df,
                work_id=work_id,
                task_id=task_id,
            )

        # Fallback to LangGraph LLM-backed workflow
        return await self._run_analysis_graph(
            request=request,
            dataset_path=dataset_path,
            data_profile=data_profile,
            df=df,
            work_id=work_id,
            task_id=task_id,
        )

    async def _run_analysis_deterministic(
        self,
        *,
        request: ExecutionRequest,
        planner: DataAnalysisPlannerPort,
        dataset_path: str,
        data_profile: Any,
        data_profile_id: UUID | None,
        df: pd.DataFrame,
        work_id: str,
        task_id: UUID,
    ) -> DataExplorerResult:
        capability = Capability.DATA_ANALYSIS
        planning_request = DataAnalysisPlanningRequest(
            task_instruction=request.input.task.instruction,
            data_profile=data_profile,
        )
        try:
            plan: DataAnalysisPlan = await planner.propose(planning_request)
        except UnsupportedAnalysisRequest as exc:
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="unsupported_analysis_request",
                message=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="analysis_planning_failed",
                message=f"Analysis planner raised an unexpected error: {exc}",
            )

        # Execute the deterministic tool.
        digest = compute_dataset_digest(dataset_path)
        try:
            payload = execute_analysis(plan, df)
        except ColumnNotFoundError as exc:
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="column_not_found",
                message=str(exc),
            )
        except InvalidToolResultError as exc:
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="invalid_result",
                message=str(exc),
            )
        except DataToolError as exc:
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code=getattr(exc, "code", "tool_execution_error"),
                message=str(exc),
            )
        except Exception as exc:  # noqa: BLE001
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="tool_execution_error",
                message=f"Unexpected tool error: {exc}",
            )

        # Validate payload is JSON-serializable.
        try:
            normalize_json_value(payload)
        except InvalidToolResultError as exc:
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="invalid_result",
                message=str(exc),
            )

        provenance = DataExecutionProvenance(
            dataset_reference=dataset_path,
            dataset_digest=digest,
            data_profile_id=data_profile_id,
            tool_reference=tool_reference(plan.operation.value),
            operation=plan.operation,
            parameters=plan.bounded_parameters(),
        )

        column_names = list(plan.columns) if plan.columns else []
        obs = DataExplorerObservation(
            observation_type=plan.operation.value,
            summary=f"Completed {plan.operation.value} on dataset.",
            payload=payload,
            artifact_refs=column_names,
        )

        return DataExplorerResult(
            source_role=_SOURCE_ROLE,
            task_id=task_id,
            work_id=work_id,
            status=ExecutionStatus.SUCCEEDED,
            capability=capability,
            observations=[obs],
            analysis_plan=plan,
            provenance=provenance,
        )

    async def _run_analysis_graph(
        self,
        *,
        request: ExecutionRequest,
        dataset_path: str,
        data_profile: Any,
        df: pd.DataFrame,
        work_id: str,
        task_id: UUID,
    ) -> DataExplorerResult:
        from cognieda.agents.data_explorer.context import Context, DEInput
        from cognieda.agents.data_explorer.model import DataExplorerModel
        from cognieda.agents.data_explorer.types import State
        from cognieda.agents.data_explorer.graph import build_graph

        capability = Capability.DATA_ANALYSIS

        de_model = self._de_model
        if de_model is None:
            if self._agent_factory is None:
                return self._failed(
                    capability=capability,
                    work_id=work_id,
                    task_id=task_id,
                    code="missing_agent_factory",
                    message="DataExplorer requires agent_factory to run the LangGraph workflow.",
                )
            de_model = DataExplorerModel(
                agent_factory=self._agent_factory,
                model_config=self._config,
            )

        digest = compute_dataset_digest(dataset_path)

        de_input = DEInput(
            task_instruction=request.input.task.instruction,
            dataset_path=dataset_path,
            dataset_digest=digest,
            data_profile=data_profile,
            dataframe=df,
        )

        context = Context(
            de_model=de_model,
            de_input=de_input,
        )

        initial_state = State(
            task_id=task_id,
            objective_id=request.input.task.objective_id,
            task_instruction=request.input.task.instruction,
            dataset_path=dataset_path,
            dataset_digest=digest,
            data_profile=data_profile,
            max_iterations=3,
        )

        try:
            graph = build_graph()
            final_state = await graph.ainvoke(
                initial_state.model_dump(),
                config={"configurable": {}},
                context=context,
            )
            final_state_obj = State.model_validate(final_state)
        except Exception as exc:  # noqa: BLE001
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="graph_execution_failed",
                message=f"Graph execution failed: {exc}",
            )

        if final_state_obj.workflow_status in ("failed", "blocked"):
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="evaluation_failed",
                message=final_state_obj.failure_reason or "Unknown failure from graph.",
            )

        if final_state_obj.emitted_evidence is None:
            return self._failed(
                capability=capability,
                work_id=work_id,
                task_id=task_id,
                code="missing_evidence",
                message="Graph succeeded but emitted no evidence.",
            )

        # Extract summary and payload from the nested Evidence content
        # Evidence content has the shape: {step_id: {"summary": "...", ...}}
        content_vals = list(final_state_obj.emitted_evidence.content.values())
        if content_vals and isinstance(content_vals[0], dict):
            summary = str(content_vals[0].get("summary", "Analysis completed."))
            payload = content_vals[0]
        else:
            summary = "Analysis completed."
            payload = {"data": final_state_obj.emitted_evidence.content}

        obs = DataExplorerObservation(
            observation_type="semantic_evidence",
            summary=summary,
            payload=payload,
            artifact_refs=[],
        )

        from cognieda.agents.data_explorer.contracts import DataExecutionProvenance, DataAnalysisPlan, DataAnalysisOperation
        
        # Map EvidenceProvenance to DataExecutionProvenance for legacy compat
        provenance = DataExecutionProvenance(
            dataset_reference=dataset_path,
            dataset_digest=digest,
            data_profile_id=data_profile.data_profile_id,
            tool_reference="cognieda.data_explorer.langgraph_agent:v1",
            operation=DataAnalysisOperation.GRAPH_MULTI_STEP if capability == Capability.DATA_ANALYSIS else "dataset_profile",
            parameters={},
            code_reference=None,
        )

        # Construct a compliant dummy plan for DATA_ANALYSIS since LangGraph is non-deterministic
        plan = DataAnalysisPlan(
            operation=DataAnalysisOperation.GRAPH_MULTI_STEP,
            columns=()
        ) if capability == Capability.DATA_ANALYSIS else None

        return DataExplorerResult(
            source_role=_SOURCE_ROLE,
            task_id=task_id,
            work_id=work_id,
            status=ExecutionStatus.SUCCEEDED,
            capability=capability,
            observations=[obs],
            produced_data_profile=final_state_obj.emitted_data_profile,
            provenance=provenance,
            analysis_plan=plan,
        )

    # -----------------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------------

    @staticmethod
    def _failed(
        *,
        capability: Capability,
        work_id: str,
        task_id: UUID,
        code: str,
        message: str,
    ) -> DataExplorerResult:
        return DataExplorerResult(
            source_role=_SOURCE_ROLE,
            task_id=task_id,
            work_id=work_id,
            status=ExecutionStatus.FAILED,
            capability=capability,
            failure=ExecutionFailure(code=code, message=message),
        )

    @staticmethod
    def _blocked(
        *,
        capability: Capability,
        work_id: str,
        task_id: UUID,
        code: str,
        message: str,
    ) -> DataExplorerResult:
        return DataExplorerResult(
            source_role=_SOURCE_ROLE,
            task_id=task_id,
            work_id=work_id,
            status=ExecutionStatus.BLOCKED,
            capability=capability,
            failure=ExecutionFailure(code=code, message=message),
        )


# ---------------------------------------------------------------------------
# Dataset loading helpers
# ---------------------------------------------------------------------------


class _InvalidDatasetBinding(ValueError):
    pass


def _require_absolute_path(raw_path: str | None) -> str:
    """Validate and resolve dataset_path to an absolute path.

    Rules (matching test_no_environment_or_process_cwd_dataset_authority):
    - None path → fail with invalid_dataset_binding
    - Relative path → fail with invalid_dataset_binding (no CWD authority)
    - No COGNIEDA_DE_DATASET_PATH env fallback
    - Absolute path → resolve and return
    """
    if raw_path is None:
        raise _InvalidDatasetBinding(
            "No dataset_path provided. Supply an absolute path in ExecutorContext."
        )
    p = Path(raw_path)
    if not p.is_absolute():
        raise _InvalidDatasetBinding(
            f"Dataset path must be an absolute path; got relative: {raw_path!r}. "
            "The Data Explorer does not use process CWD or environment fallbacks."
        )
    return str(p.resolve())


def _resolve_absolute_path(path: str) -> str:
    """Resolve any path to absolute (for use in profile_candidate)."""
    return str(Path(path).resolve())


def _load_df(dataset_path: str) -> pd.DataFrame:
    """Load a CSV or Parquet dataset into a DataFrame.

    Raises FileNotFoundError if the file does not exist.
    """
    p = Path(dataset_path)
    if not p.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")
    if p.suffix == ".csv":
        return pd.read_csv(p)
    if p.suffix == ".parquet":
        return pd.read_parquet(p)
    raise ValueError(f"Unsupported file type '{p.suffix}'. Use .csv or .parquet.")


__all__ = ("DataExplorer",)

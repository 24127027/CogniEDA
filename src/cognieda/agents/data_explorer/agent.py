"""Data Explorer capability provider."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from pydantic_ai import Agent

from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.delegation import Capability, ExecutionFailure, ExecutionRequest, ExecutionStatus
from cognieda.infrastructure.datasets import load_dataset
from cognieda.schemas.enums import TaskKind

from .contracts import (
    DataAnalysisPlan,
    DataAnalysisPlannerPort,
    DataAnalysisPlanningRequest,
    DataExecutionProvenance,
    DataExplorerInput,
    DataExplorerObservation,
    DataExplorerResult,
    DataProfileCandidate,
)
from .planning import ModelDataAnalysisPlanner, UnsupportedAnalysisRequest
from .tools import (
    DataToolError,
    InvalidToolResultError,
    execute_analysis,
    normalize_json_value,
    profile_dataset,
    tool_reference,
)


def create_de_agent(config: ModelConfig, agent_factory: AgentFactoryPort) -> Agent[None]:
    return agent_factory.create_agent(
        worker="data_explorer",
        config=config,
        deps_type=type(None),
        builtin_tools=(),
    )


@dataclass(slots=True)
class DataExplorerConfig:
    model: ModelConfig | None = None


class DataExplorer:
    """Provider for bounded data analysis and profiling capability requests."""

    builtin_tools: tuple[()] = ()

    def __init__(
        self,
        *,
        config: ModelConfig | None = None,
        agent_factory: AgentFactoryPort | None = None,
        analysis_planner: DataAnalysisPlannerPort | None = None,
    ) -> None:
        if agent_factory is not None and config is None:
            raise ValueError(
                "Model configuration is required when an agent factory is provided."
            )

        self.config = config
        self.agent_factory = agent_factory
        self.analysis_planner = analysis_planner or (
            ModelDataAnalysisPlanner(config=config, agent_factory=agent_factory)
            if agent_factory is not None and config is not None
            else None
        )

    @staticmethod
    def _work_id() -> str:
        return f"de:{uuid4()}"

    @staticmethod
    def _dataset_path(request: ExecutionRequest) -> Path:
        raw_path = request.context.dataset_path
        if raw_path is None or not raw_path.strip():
            raise DataToolError("Data Explorer requires an explicit dataset_path.")
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            raise DataToolError("Data Explorer requires an absolute explicit dataset_path.")
        return path.resolve()

    @staticmethod
    def _failure(
        request: ExecutionRequest,
        work_id: str,
        *,
        code: str,
        message: str,
    ) -> DataExplorerResult:
        return DataExplorerResult(
            source_role="data_explorer",
            task_id=request.input.task.task_id,
            work_id=work_id,
            status=ExecutionStatus.FAILED,
            capability=request.capability,
            failure=ExecutionFailure(code=code, message=message),
        )

    def profile_candidate(self, dataset_path: str) -> DataProfileCandidate:
        """Create a non-authoritative initial profile candidate without a fake Task."""

        raw_path = Path(dataset_path).expanduser()
        if not raw_path.is_absolute():
            raise DataToolError("Initial profiling requires an absolute explicit dataset_path.")
        loaded = load_dataset(raw_path.resolve())
        profile = profile_dataset(loaded.dataframe.copy(deep=True))
        return DataProfileCandidate(
            work_id=self._work_id(),
            profile=profile,
            provenance=DataExecutionProvenance(
                dataset_reference=str(loaded.path),
                dataset_digest=loaded.dataset_digest,
                data_profile_id=None,
                tool_reference="cognieda.data_explorer.dataset_profile:v1",
                operation="dataset_profile",
                parameters={"mode": "candidate"},
            ),
        )

    async def run(self, request: ExecutionRequest) -> DataExplorerResult:
        work_id = self._work_id()
        if request.input.task.kind is not TaskKind.DATA:
            return self._failure(
                request,
                work_id,
                code="unsupported_task_kind",
                message="Data Explorer accepts only DATA Tasks.",
            )
        if request.capability == Capability.DATA_TRANSFORMATION:
            return DataExplorerResult(
                source_role="data_explorer",
                task_id=request.input.task.task_id,
                work_id=work_id,
                status=ExecutionStatus.BLOCKED,
                capability=request.capability,
                limitations=[
                    "Successor dataset and DataProfile creation are deferred beyond M3-A."
                ],
                failure=ExecutionFailure(
                    code="successor_data_profile_not_implemented",
                    message=(
                        "DATA_TRANSFORMATION is blocked because it cannot yet create a "
                        "successor dataset state and DataProfile."
                    ),
                ),
            )
        if request.capability not in {
            Capability.DATA_ANALYSIS,
            Capability.DATA_PROFILING,
        }:
            raise ValueError(f"Data Explorer cannot provide {request.capability}.")

        try:
            dataset_path = self._dataset_path(request)
            loaded = load_dataset(dataset_path)
        except FileNotFoundError as exc:
            return self._failure(
                request,
                work_id,
                code="dataset_not_found",
                message=str(exc),
            )
        except DataToolError as exc:
            return self._failure(
                request,
                work_id,
                code="invalid_dataset_binding",
                message=str(exc),
            )
        except ValueError as exc:
            return self._failure(
                request,
                work_id,
                code="unsupported_dataset_format",
                message=str(exc),
            )
        except Exception as exc:
            return self._failure(
                request,
                work_id,
                code="tool_execution_error",
                message=f"Dataset loading failed: {exc}",
            )

        dataset_reference = str(loaded.path)
        dataset_digest = loaded.dataset_digest
        dataframe = loaded.dataframe.copy(deep=True)

        if request.capability is Capability.DATA_ANALYSIS:
            if request.context.data_profile_id is None:
                return self._failure(
                    request,
                    work_id,
                    code="missing_data_profile_binding",
                    message="DATA_ANALYSIS requires an explicit data_profile_id.",
                )
            if not isinstance(request.input, DataExplorerInput):
                return self._failure(
                    request,
                    work_id,
                    code="missing_data_profile_binding",
                    message=(
                        "DATA_ANALYSIS requires the role-specific authoritative DataProfile "
                        "projection for planning."
                    ),
                )
            profile = request.input.data_profile
            if profile.data_profile_id != request.context.data_profile_id:
                return self._failure(
                    request,
                    work_id,
                    code="invalid_dataset_binding",
                    message="The Data Explorer profile projection does not match data_profile_id.",
                )
            if self.analysis_planner is None:
                return self._failure(
                    request,
                    work_id,
                    code="analysis_planning_unavailable",
                    message="No Data Explorer analysis planning adapter is configured.",
                )
            try:
                proposed_plan = await self.analysis_planner.propose(
                    DataAnalysisPlanningRequest(
                        task_instruction=request.input.task.instruction,
                        data_profile=profile,
                    )
                )
                plan = DataAnalysisPlan.model_validate(proposed_plan)
            except UnsupportedAnalysisRequest as exc:
                return self._failure(
                    request,
                    work_id,
                    code="unsupported_analysis_request",
                    message=str(exc),
                )
            except (TypeError, ValueError) as exc:
                return self._failure(
                    request,
                    work_id,
                    code="invalid_analysis_plan",
                    message=f"Data Explorer planning returned an invalid plan: {exc}",
                )
            except Exception as exc:
                return self._failure(
                    request,
                    work_id,
                    code="analysis_planning_failed",
                    message=f"Data Explorer planning failed: {exc}",
                )
            try:
                normalized_payload = normalize_json_value(execute_analysis(dataframe, plan))
                if not isinstance(normalized_payload, dict) or not normalized_payload:
                    raise InvalidToolResultError(
                        "A deterministic analysis must return a non-empty object."
                    )
                payload = normalized_payload
            except DataToolError as exc:
                return self._failure(
                    request,
                    work_id,
                    code=exc.code,
                    message=str(exc),
                )
            except Exception as exc:
                return self._failure(
                    request,
                    work_id,
                    code="tool_execution_error",
                    message=f"Deterministic analysis failed: {exc}",
                )

            return DataExplorerResult(
                source_role="data_explorer",
                task_id=request.input.task.task_id,
                work_id=work_id,
                status=ExecutionStatus.SUCCEEDED,
                capability=request.capability,
                observations=[
                    DataExplorerObservation(
                        observation_type="deterministic_data_analysis",
                        summary=f"Executed {plan.operation.value} with validated parameters.",
                        payload=payload,
                    )
                ],
                provenance=DataExecutionProvenance(
                    dataset_reference=dataset_reference,
                    dataset_digest=dataset_digest,
                    data_profile_id=request.context.data_profile_id,
                    tool_reference=tool_reference(plan.operation),
                    operation=plan.operation,
                    parameters=plan.bounded_parameters(),
                ),
                analysis_plan=plan,
            )

        try:
            profile = profile_dataset(dataframe)
        except Exception as exc:
            return self._failure(
                request,
                work_id,
                code="tool_execution_error",
                message=f"Deterministic profiling failed: {exc}",
            )

        profile_id = request.context.data_profile_id
        provenance = DataExecutionProvenance(
            dataset_reference=dataset_reference,
            dataset_digest=dataset_digest,
            data_profile_id=profile_id,
            tool_reference="cognieda.data_explorer.dataset_profile:v1",
            operation="dataset_profile",
            parameters={
                "mode": "candidate" if profile_id is None else "existing_profile_observation"
            },
        )
        if profile_id is None:
            return DataExplorerResult(
                source_role="data_explorer",
                task_id=request.input.task.task_id,
                work_id=work_id,
                status=ExecutionStatus.SUCCEEDED,
                capability=request.capability,
                produced_data_profile=profile,
                provenance=provenance,
            )
        if profile.column_count > 50:
            return self._failure(
                request,
                work_id,
                code="invalid_result",
                message="Evidence-producing profiling is limited to 50 columns.",
            )
        return DataExplorerResult(
            source_role="data_explorer",
            task_id=request.input.task.task_id,
            work_id=work_id,
            status=ExecutionStatus.SUCCEEDED,
            capability=request.capability,
            observations=[
                DataExplorerObservation(
                    observation_type="deterministic_dataset_profile",
                    summary="Executed deterministic profiling for the bound DataProfile.",
                    payload=profile.model_dump(
                        mode="json", exclude={"data_profile_id"}
                    ),
                )
            ],
            provenance=provenance,
        )


DataExplorerExecutor = DataExplorer

__all__ = (
    "DataExplorer",
    "DataExplorerConfig",
    "DataExplorerExecutor",
    "DataExplorerResult",
    "DataProfileCandidate",
    "create_de_agent",
)

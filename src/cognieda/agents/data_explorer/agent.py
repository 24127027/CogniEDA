"""Data Explorer agent — entry point for the LangGraph-backed MVP workflow."""

from __future__ import annotations

from uuid import UUID

from cognieda.application.ports import AgentFactoryPort, ModelConfig
from cognieda.delegation import Capability, ExecutionFailure, ExecutionRequest, ExecutionStatus
from cognieda.infrastructure.datasets import load_dataset
from cognieda.schemas.enums import TaskKind

from .context import Context, DEInput
from .graph import build_graph
from .model import DataExplorerDecisionModel, DataExplorerModel
from .types import (
    DEControlledError,
    DEErrorCode,
    DataExplorerOutput,
    State,
)


class DataExplorer:
    """Self-contained Data Explorer backed by a LangGraph planning-execute-check loop.

    Callers (Planner, Hypothesis Analyst) invoke `run` with a DEInput and
    receive a strongly typed DataExplorerOutput containing either an admitted
    Evidence object, an admitted DataProfile, or a controlled error.
    """

    CAPABILITIES: tuple[Capability, ...] = (
        Capability.DATA_ANALYSIS,
        Capability.DATA_PROFILING,
        Capability.DATA_TRANSFORMATION,
    )

    def __init__(
        self,
        *,
        de_model: DataExplorerDecisionModel | None = None,
        agent_factory: AgentFactoryPort | None = None,
        model_config: ModelConfig | None = None,
        agent_instruction: str = "",
        max_iterations: int = 3,
    ) -> None:
        if de_model is not None:
            if agent_factory is not None or model_config is not None:
                raise ValueError(
                    "Provide either de_model or agent_factory plus model_config, not both."
                )
            self.model: DataExplorerDecisionModel = de_model
        else:
            if agent_factory is None or model_config is None:
                raise ValueError(
                    "DataExplorer requires a typed de_model or agent_factory plus model_config."
                )
            self.model = DataExplorerModel(
                agent_factory=agent_factory,
                model_config=model_config,
                agent_instruction=agent_instruction or None,
            )

        self.max_iterations = max_iterations
        self.graph = build_graph()

    async def run(
        self,
        task_id: UUID,
        de_input: DEInput,
        *,
        objective_id: UUID | None = None,
    ) -> DataExplorerOutput:
        """Execute the full planning-execute-check_result loop and return typed output."""
        state = State(
            task_id=task_id,
            objective_id=objective_id,
            task_instruction=de_input.task_instruction,
            dataset_path=de_input.dataset_path,
            dataset_digest=de_input.dataset_digest,
            data_profile=de_input.data_profile,
            max_iterations=self.max_iterations,
        )
        context = Context(de_model=self.model, de_input=de_input)

        raw_result = await self.graph.ainvoke(state, context=context)
        final_state = State.model_validate(raw_result)

        if final_state.workflow_status == "succeeded":
            if final_state.emitted_evidence is not None:
                return DataExplorerOutput(
                    task_id=task_id,
                    evidence=final_state.emitted_evidence,
                    summary="Data Explorer completed analysis and admitted Evidence.",
                )
            if final_state.emitted_data_profile is not None:
                return DataExplorerOutput(
                    task_id=task_id,
                    data_profile=final_state.emitted_data_profile,
                    summary="Data Explorer completed profiling and admitted DataProfile.",
                )
            # Succeeded without emitting output — treated as an internal error
            error = DEControlledError(
                code=DEErrorCode.EVIDENCE_CONSTRUCTION_FAILED,
                message="Data Explorer workflow completed without admitted output.",
            )
            return DataExplorerOutput(
                task_id=task_id,
                summary=error.message,
                error=error,
            )

        reason = final_state.failure_reason or "Data Explorer workflow ended without output."
        code = (
            DEErrorCode.UNFEASIBLE_REQUEST
            if final_state.workflow_status == "blocked"
            else DEErrorCode.EXECUTION_FAILED
        )
        error = DEControlledError(code=code, message=reason)
        return DataExplorerOutput(task_id=task_id, summary=reason, error=error)


__all__ = ("DataExplorer",)

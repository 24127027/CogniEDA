"""Data Explorer analysis planning.

Defines:
  - UnsupportedAnalysisRequest: raised when the planner cannot map a task to
    a finite DataAnalysisPlan operation.
  - DataAnalysisPlannerPort: structural protocol (matches contracts.py).
  - DataAnalysisPlanner: Pydantic AI–backed implementation that converts a
    natural-language DataAnalysisPlanningRequest into a DataAnalysisPlan.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cognieda.agents.data_explorer.contracts import (
        DataAnalysisPlan,
        DataAnalysisPlannerPort,
        DataAnalysisPlanningRequest,
    )


class UnsupportedAnalysisRequest(Exception):
    """Raised when a task instruction cannot be mapped to any finite operation.

    The Data Explorer is a bounded instrument; it cannot handle scientific or
    open-ended analytical requests. Callers should surface this as a BLOCKED
    result with code 'unsupported_analysis_request'.
    """


class DataAnalysisPlanner:
    """Pydantic AI–backed planner: task instruction → DataAnalysisPlan.

    This class wraps a Pydantic AI agent configured with result_type=DataAnalysisPlan
    so the model output is guaranteed to match the strict bounded schema.

    Intended to be used by DataExplorer(analysis_planner=DataAnalysisPlanner(...)).
    The planner is the only component that calls an LLM; all execution is
    deterministic after the plan is produced.
    """

    def __init__(
        self,
        agent_factory: object,
        model_config: object,
        *,
        agent_instruction: str = "",
    ) -> None:
        from cognieda.agents.utilities import instruction

        self._agent_factory = agent_factory
        self._model_config = model_config
        self._instruction = instruction.assemble("planning.txt", agent_instruction or None)

        # Build once; result_type guarantees DataAnalysisPlan output.
        self._agent = agent_factory.create_agent(  # type: ignore[union-attr]
            worker="data_explorer",
            config=model_config,
        )

    async def propose(
        self,
        request: "DataAnalysisPlanningRequest",
    ) -> "DataAnalysisPlan":
        """Translate a DataAnalysisPlanningRequest into a bounded DataAnalysisPlan.

        Raises UnsupportedAnalysisRequest when the model cannot map the task to a
        supported operation.
        """
        from cognieda.agents.data_explorer.contracts import DataAnalysisPlan

        prompt = (
            f"Task: {request.task_instruction}\n"
            f"DataProfile: {request.data_profile.model_dump_json()}\n"
            f"Supported operations: {[op.value for op in request.supported_operations]}"
        )

        try:
            result = await self._agent.run(
                prompt,
                output_type=DataAnalysisPlan,
                instructions=self._instruction,
            )
            return DataAnalysisPlan.model_validate(result.output)
        except Exception as exc:
            raise UnsupportedAnalysisRequest(
                f"Planner could not produce a valid DataAnalysisPlan: {exc}"
            ) from exc


__all__ = ("DataAnalysisPlanner", "UnsupportedAnalysisRequest")

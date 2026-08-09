from __future__ import annotations

from collections.abc import Sequence

from pydantic import ConfigDict, Field
from pydantic_ai.messages import ModelMessage

from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Evidence,
    Objective,
    SessionFrame,
    Task,
)
from cognieda.schemas.common import CogniEDABaseModel


class PlanningContext(CogniEDABaseModel):
    """Ephemeral materialized research context selected for one Planner run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    latest_request: str = Field(min_length=1)
    objective: Objective | None = None
    assumptions: tuple[Assumption, ...] = ()
    tasks: tuple[Task, ...] = ()
    evidences: tuple[Evidence, ...] = ()
    data_profile: DataProfile | None = None
    message_history: tuple[ModelMessage, ...] = ()

    @classmethod
    def from_frame(
        cls,
        *,
        latest_request: str,
        frame: SessionFrame,
        message_history: Sequence[ModelMessage] = (),
    ) -> PlanningContext:
        """Materialize the current pre-reference-migration SessionFrame state."""

        return cls(
            latest_request=latest_request,
            objective=frame.objective,
            assumptions=frame.assumptions,
            tasks=frame.tasks,
            evidences=frame.evidences,
            data_profile=frame.data_profile,
            message_history=tuple(message_history),
        )

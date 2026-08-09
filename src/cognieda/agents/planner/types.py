from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from cognieda.execution import Capability, ExecutorContext, PlannerWorkOutcome
from cognieda.schemas.artifacts import (
    Assumption,
    DataProfile,
    Evidence,
    Objective,
    SessionFrame,
    Task,
)


class PlannerAction(StrEnum):
    """Small finite action space owned by the MVP Planner."""

    ANSWER_FROM_STATE = "answer_from_state"
    SET_OR_REFINE_OBJECTIVE = "set_or_refine_objective"
    ADD_ASSUMPTION = "add_assumption"
    CREATE_OR_RUN_DATA_TASK = "create_or_run_data_task"
    STATE_SUMMARY = "state_summary"
    INVALID_OR_UNSUPPORTED = "invalid_or_unsupported"


class PlannerErrorCode(StrEnum):
    INVALID_COMMAND = "invalid_command"
    MODEL_UNAVAILABLE = "model_unavailable"
    INVALID_MODEL_DECISION = "invalid_model_decision"
    UNSUPPORTED_ACTION = "unsupported_action"
    MISSING_OBJECTIVE = "missing_objective"
    DISPATCH_FAILED = "dispatch_failed"
    TASK_OUTCOME_MISMATCH = "task_outcome_mismatch"
    INVALID_SUCCESSOR_STATE = "invalid_successor_state"
    NO_ADMITTED_EVIDENCE = "no_admitted_evidence"
    RESPONSE_FAILED = "response_failed"


class PlannerControlledError(BaseModel):
    """Application-facing failure that does not leak an arbitrary exception."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: PlannerErrorCode
    message: str = Field(min_length=1)


class PlannerConversationTurn(BaseModel):
    """Non-authoritative conversation projection used only for request understanding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    human_message: str
    planner_message: str = Field(min_length=1)


class PlannerDecision(BaseModel):
    """Typed semantic proposal returned by request understanding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    action: PlannerAction
    objective_text: str | None = Field(default=None, min_length=1)
    assumption_text: str | None = Field(default=None, min_length=1)
    task_instruction: str | None = Field(default=None, min_length=1)
    capability: Capability | None = None
    message: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def _fields_match_action(self) -> PlannerDecision:
        if self.action is PlannerAction.SET_OR_REFINE_OBJECTIVE:
            if self.objective_text is None:
                raise ValueError("Objective actions require objective_text.")
            if any(
                value is not None
                for value in (self.assumption_text, self.task_instruction, self.capability)
            ):
                raise ValueError("Objective actions cannot propose other state changes.")
        elif self.action is PlannerAction.ADD_ASSUMPTION:
            if self.assumption_text is None:
                raise ValueError("Assumption actions require assumption_text.")
            if any(
                value is not None
                for value in (self.objective_text, self.task_instruction, self.capability)
            ):
                raise ValueError("Assumption actions cannot propose other state changes.")
        elif self.action is PlannerAction.CREATE_OR_RUN_DATA_TASK:
            if self.task_instruction is None or self.capability is None:
                raise ValueError("Data work requires task_instruction and capability.")
            if self.assumption_text is not None:
                raise ValueError("A data-work decision cannot add an Assumption.")
            if self.capability not in {
                Capability.DATA_ANALYSIS,
                Capability.DATA_PROFILING,
                Capability.DATA_TRANSFORMATION,
            }:
                raise ValueError("MVP Planner data work requires a Data Explorer capability.")
        elif any(
            value is not None
            for value in (
                self.objective_text,
                self.assumption_text,
                self.task_instruction,
                self.capability,
            )
        ):
            raise ValueError("This Planner action cannot propose research-state changes.")

        if self.action is PlannerAction.INVALID_OR_UNSUPPORTED and self.message is None:
            raise ValueError("An invalid or unsupported decision requires a message.")
        return self


class PlannerModelInput(BaseModel):
    """Typed initial context used for one request-understanding invocation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    latest_request: str = Field(min_length=1)
    objective: Objective | None = None
    assumptions: tuple[Assumption, ...] = ()
    tasks: tuple[Task, ...] = ()
    data_profile: DataProfile | None = None
    evidences: tuple[Evidence, ...] = ()
    conversation: tuple[PlannerConversationTurn, ...] = ()

    @classmethod
    def from_frame(
        cls,
        latest_request: str,
        frame: SessionFrame,
        *,
        conversation: tuple[PlannerConversationTurn, ...] = (),
    ) -> PlannerModelInput:
        return cls(
            latest_request=latest_request,
            objective=frame.objective,
            assumptions=frame.assumptions,
            tasks=frame.tasks,
            data_profile=frame.data_profile,
            evidences=frame.evidences,
            conversation=conversation,
        )


class PlannerAnswerInput(BaseModel):
    """Evidence-only answer context; planning Assumptions are deliberately absent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    latest_request: str = Field(min_length=1)
    objective: Objective | None = None
    data_profile: DataProfile | None = None
    evidences: tuple[Evidence, ...] = Field(min_length=1)


class PlannerResponseDraft(BaseModel):
    """Typed human-facing prose drafted only from an authorized bounded input."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(min_length=1)


class State(BaseModel):
    """Transient state for one deterministic MVP Planner invocation."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    session_frame: SessionFrame
    conversation_context: tuple[PlannerConversationTurn, ...] = ()
    execution_context: ExecutorContext = Field(default_factory=ExecutorContext)
    decision: PlannerDecision | None = None
    created_task_id: UUID | None = None
    selected_capability: Capability | None = None
    work_outcome: PlannerWorkOutcome | None = None
    response: str | None = None
    error: PlannerControlledError | None = None


class Context(BaseModel):
    """Injected model and dispatcher boundaries available to graph nodes."""

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")

    planner_model: object
    dispatcher: object


class PlannerOutput(BaseModel):
    """Strongly typed application-facing result for one Planner turn."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    response: str = Field(min_length=1)
    session_frame: SessionFrame
    decision: PlannerDecision | None = None
    created_task_ids: tuple[UUID, ...] = ()
    selected_capability: Capability | None = None
    work_outcome: PlannerWorkOutcome | None = None
    error: PlannerControlledError | None = None

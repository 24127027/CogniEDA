
from __future__ import annotations

from pydantic import Field, model_validator
from uuid import UUID, uuid4

from cognieda.schemas.common import CogniEDABaseModel
from cognieda.schemas.artifacts import (
    Objective,
    Assumption,
    Task,
    Evidence,
    DataProfile,
)
from cognieda.schemas.enums import TaskStatus

from .conversation import ConversationHistory

# TODO: When knowledge graph ready
# use ids for object representation instead of full objects
class SessionFrame(CogniEDABaseModel):
    """Authoritative typed research state for the single active MVP session."""

    objective: Objective | None = None
    assumptions: tuple[Assumption, ...] = ()
    tasks: tuple[Task, ...] = ()
    evidences: tuple[Evidence, ...] = ()
    data_profile: DataProfile | None = None
    conversation: ConversationHistory = Field(default_factory=ConversationHistory)

    @model_validator(mode="after")
    def _validate_research_state(self) -> SessionFrame:
        self._check_research_state()
        return self

    def _check_research_state(self) -> None:
        self._reject_duplicate_ids(
            [assumption.assumption_id for assumption in self.assumptions],
            object_name="Assumption",
        )
        self._reject_duplicate_ids(
            [task.task_id for task in self.tasks],
            object_name="Task",
        )
        self._reject_duplicate_ids(
            [evidence.evidence_id for evidence in self.evidences],
            object_name="Evidence",
        )

        tasks_by_id = {
            task.task_id: task
            for task in self.tasks
        }

        for evidence in self.evidences:
            task = tasks_by_id.get(evidence.task_id)

            # MVP integrity check:
            # only validate the Task when it is present in the frame.
            if task is not None and task.status is not TaskStatus.COMPLETED:
                raise ValueError(
                    "Selected Evidence cannot reference "
                    "a selected non-completed Task."
                )

            # Same principle for DataProfile.
            if (
                self.data_profile is not None
                and evidence.data_profile_id
                != self.data_profile.data_profile_id
            ):
                raise ValueError(
                    "Selected Evidence and selected DataProfile "
                    "must refer to the same dataset state."
                )

    @staticmethod
    def _reject_duplicate_ids(ids: list[UUID], *, object_name: str) -> None:
        if len(ids) != len(set(ids)):
            raise ValueError(f"SessionFrame rejects duplicate {object_name} IDs.")

    def _validated_copy(self, **updates: object) -> SessionFrame:
        values: dict[str, object] = {
            "objective": self.objective,
            "assumptions": self.assumptions,
            "tasks": self.tasks,
            "evidences": self.evidences,
            "data_profile": self.data_profile,
            "conversation": self.conversation,
        }
        values.update(updates)
        return SessionFrame.model_validate(values)

    def set_objective(self, objective: Objective | None) -> SessionFrame:
        return self._validated_copy(objective=objective)

    def add_assumption(self, assumption: Assumption) -> SessionFrame:
        if any(item.assumption_id == assumption.assumption_id for item in self.assumptions):
            raise ValueError("SessionFrame rejects duplicate Assumption IDs.")
        return self._validated_copy(assumptions=(*self.assumptions, assumption))

    def add_task(self, task: Task) -> SessionFrame:
        if any(item.task_id == task.task_id for item in self.tasks):
            raise ValueError("SessionFrame rejects duplicate Task IDs.")
        return self._validated_copy(tasks=(*self.tasks, task))

    def set_task_status(self, task_id: UUID, status: TaskStatus) -> SessionFrame:
        for index, task in enumerate(self.tasks):
            if task.task_id == task_id:
                replacement = Task(
                    task_id=task.task_id,
                    instruction=task.instruction,
                    status=status,
                )
                return self._validated_copy(
                    tasks=(
                        *self.tasks[:index],
                        replacement,
                        *self.tasks[index + 1 :],
                    )
                )
        raise ValueError("SessionFrame cannot update a Task it does not contain.")

    def add_evidence(self, evidence: Evidence) -> SessionFrame:
        return self._validated_copy(evidences=(*self.evidences, evidence))

    def set_data_profile(self, data_profile: DataProfile | None) -> SessionFrame:
        return self._validated_copy(data_profile=data_profile)

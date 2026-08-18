"""Immutable minimal Plan domain and structural validation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection
from uuid import UUID, uuid4

from pydantic import Field, computed_field, field_validator, model_validator

from cognieda.schemas.artifacts import Assumption, Objective, Task
from cognieda.schemas.common import ImmutableCogniEDABaseModel


class PlanDependency(ImmutableCogniEDABaseModel):
    """All direct outgoing dependency edges from one prerequisite Task."""

    prerequisite_task_id: UUID
    dependent_task_ids: tuple[UUID, ...] = Field(min_length=1)

    @field_validator("dependent_task_ids", mode="after")
    @classmethod
    def _canonicalize_dependent_task_ids(
        cls,
        dependent_task_ids: tuple[UUID, ...],
    ) -> tuple[UUID, ...]:
        if len(dependent_task_ids) != len(set(dependent_task_ids)):
            raise ValueError("PlanDependency rejects duplicate dependent Task IDs.")
        return tuple(sorted(dependent_task_ids, key=str))

    @model_validator(mode="after")
    def _reject_self_dependency(self) -> PlanDependency:
        if self.prerequisite_task_id in self.dependent_task_ids:
            raise ValueError("PlanDependency rejects a self dependency.")
        return self


class Plan(ImmutableCogniEDABaseModel):
    """Immutable, non-FCO Plan over one exact Objective and a Task DAG."""

    plan_id: UUID = Field(default_factory=uuid4)
    objective: Objective
    assumptions: tuple[Assumption, ...] = ()
    tasks: tuple[Task, ...] = ()
    dependencies: tuple[PlanDependency, ...] = ()

    @field_validator("assumptions", mode="after")
    @classmethod
    def _canonicalize_assumptions(
        cls,
        assumptions: tuple[Assumption, ...],
    ) -> tuple[Assumption, ...]:
        assumption_ids = [assumption.assumption_id for assumption in assumptions]
        if len(assumption_ids) != len(set(assumption_ids)):
            raise ValueError("Plan rejects duplicate Assumption identities.")
        return tuple(sorted(assumptions, key=lambda item: str(item.assumption_id)))

    @field_validator("tasks", mode="after")
    @classmethod
    def _canonicalize_tasks(cls, tasks: tuple[Task, ...]) -> tuple[Task, ...]:
        task_ids = [task.task_id for task in tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Plan rejects duplicate Task identities.")
        return tuple(sorted(tasks, key=lambda item: str(item.task_id)))

    @field_validator("dependencies", mode="after")
    @classmethod
    def _canonicalize_dependencies(
        cls,
        dependencies: tuple[PlanDependency, ...],
    ) -> tuple[PlanDependency, ...]:
        prerequisite_ids = [
            dependency.prerequisite_task_id for dependency in dependencies
        ]
        if len(prerequisite_ids) != len(set(prerequisite_ids)):
            raise ValueError("Plan rejects duplicate prerequisite dependency groups.")
        return tuple(
            sorted(
                dependencies,
                key=lambda item: str(item.prerequisite_task_id),
            )
        )

    @model_validator(mode="after")
    def _validate_membership_and_dependencies(self) -> Plan:
        for task in self.tasks:
            if task.objective_id != self.objective.objective_id:
                raise ValueError("Every Plan Task must belong to the Plan Objective.")
        self._validate_dependency_graph(set(self.task_ids))
        return self

    @computed_field(return_type=tuple[UUID, ...])  # type: ignore[prop-decorator]
    @property
    def task_ids(self) -> tuple[UUID, ...]:
        """Return the exact Task identities derived from canonical membership."""

        return tuple(task.task_id for task in self.tasks)

    def _validate_dependency_graph(self, member_ids: set[UUID]) -> None:
        in_degree = dict.fromkeys(member_ids, 0)
        dependents = {task_id: set[UUID]() for task_id in member_ids}
        for dependency in self.dependencies:
            if dependency.prerequisite_task_id not in member_ids or any(
                dependent_id not in member_ids
                for dependent_id in dependency.dependent_task_ids
            ):
                raise ValueError("Plan rejects a dependency endpoint outside membership.")
            for dependent_id in dependency.dependent_task_ids:
                dependents[dependency.prerequisite_task_id].add(dependent_id)
                in_degree[dependent_id] += 1

        ready = [task_id for task_id, degree in in_degree.items() if degree == 0]
        visited = 0
        while ready:
            task_id = ready.pop()
            visited += 1
            for dependent_id in dependents[task_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    ready.append(dependent_id)
        if visited != len(member_ids):
            raise ValueError("Plan dependencies must form an acyclic graph.")

    def eligible_task_ids(
        self,
        *,
        completed_task_ids: Collection[UUID] = (),
    ) -> tuple[UUID, ...]:
        """Return eligible IDs using only membership and structural prerequisites."""

        completed = set(completed_task_ids)
        if completed.difference(self.task_ids):
            raise ValueError("Completed Task identity is outside Plan membership.")
        prerequisites = {task_id: set[UUID]() for task_id in self.task_ids}
        for dependency in self.dependencies:
            for dependent_id in dependency.dependent_task_ids:
                prerequisites[dependent_id].add(dependency.prerequisite_task_id)
        return tuple(
            task_id
            for task_id in self.task_ids
            if task_id not in completed and prerequisites[task_id].issubset(completed)
        )

    def _fingerprint_payload(self) -> dict[str, object]:
        return {
            "objective": self.objective.model_dump(mode="json"),
            "assumptions": [assumption.model_dump(mode="json") for assumption in self.assumptions],
            "tasks": [
                task.semantic_payload()
                for task in self.tasks
            ],
            "dependencies": [
                {
                    "prerequisite_task_id": str(dependency.prerequisite_task_id),
                    "dependent_task_ids": [
                        str(dependent_id)
                        for dependent_id in dependency.dependent_task_ids
                    ],
                }
                for dependency in self.dependencies
            ],
        }

    @computed_field(return_type=str)  # type: ignore[prop-decorator]
    @property
    def fingerprint(self) -> str:
        """Return the digest of exact canonical Plan semantics."""

        serialized = json.dumps(
            self._fingerprint_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(serialized).hexdigest()}"


__all__ = ("Plan", "PlanDependency")

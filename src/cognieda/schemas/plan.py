"""Immutable minimal Plan domain and structural validation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Iterable
from typing import Self
from uuid import UUID, uuid4

from pydantic import Field, computed_field, field_validator, model_validator

from cognieda.schemas.artifacts import Assumption, Objective, Task
from cognieda.schemas.common import ImmutableCogniEDABaseModel


class PlanDependency(ImmutableCogniEDABaseModel):
    """Directed structural prerequisite edge between two Tasks in one Plan."""

    prerequisite_task_id: UUID
    dependent_task_id: UUID

    @model_validator(mode="after")
    def _reject_self_dependency(self) -> PlanDependency:
        if self.prerequisite_task_id == self.dependent_task_id:
            raise ValueError("PlanDependency rejects a self dependency.")
        return self


class Plan(ImmutableCogniEDABaseModel):
    """Immutable, non-FCO Plan over one exact Objective and a Task DAG."""

    plan_id: UUID = Field(default_factory=uuid4)
    objective: Objective
    assumptions: tuple[Assumption, ...] = ()
    task_ids: tuple[UUID, ...] = ()
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

    @field_validator("task_ids", mode="after")
    @classmethod
    def _canonicalize_task_ids(cls, task_ids: tuple[UUID, ...]) -> tuple[UUID, ...]:
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Plan rejects duplicate Task IDs.")
        return tuple(sorted(task_ids, key=str))

    @field_validator("dependencies", mode="after")
    @classmethod
    def _canonicalize_dependencies(
        cls,
        dependencies: tuple[PlanDependency, ...],
    ) -> tuple[PlanDependency, ...]:
        edges = [
            (dependency.prerequisite_task_id, dependency.dependent_task_id)
            for dependency in dependencies
        ]
        if len(edges) != len(set(edges)):
            raise ValueError("Plan rejects duplicate dependency edges.")
        return tuple(
            sorted(
                dependencies,
                key=lambda item: (
                    str(item.prerequisite_task_id),
                    str(item.dependent_task_id),
                ),
            )
        )

    @model_validator(mode="after")
    def _validate_dependencies(self) -> Plan:
        self._validate_dependency_graph(set(self.task_ids))
        return self

    def validate_tasks(self, tasks: Iterable[Task]) -> None:
        """Prove exact membership and Objective scope for supplied Tasks."""

        tasks_by_id: dict[UUID, Task] = {}
        for task in tasks:
            if task.task_id in tasks_by_id:
                raise ValueError("Plan rejects duplicate Task objects.")
            tasks_by_id[task.task_id] = task

        if set(self.task_ids) != set(tasks_by_id):
            raise ValueError("Plan Task inputs must exactly match task_ids membership.")

        for task in tasks_by_id.values():
            if task.objective_id != self.objective.objective_id:
                raise ValueError("Every supplied Task must belong to the Plan Objective.")

    def _validate_dependency_graph(self, member_ids: set[UUID]) -> None:
        in_degree = dict.fromkeys(member_ids, 0)
        dependents = {task_id: set[UUID]() for task_id in member_ids}
        for dependency in self.dependencies:
            if (
                dependency.prerequisite_task_id not in member_ids
                or dependency.dependent_task_id not in member_ids
            ):
                raise ValueError("Plan rejects a dependency endpoint outside membership.")
            dependents[dependency.prerequisite_task_id].add(dependency.dependent_task_id)
            in_degree[dependency.dependent_task_id] += 1

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

    @classmethod
    def create(
        cls,
        *,
        objective: Objective,
        assumptions: Iterable[Assumption] = (),
        task_ids: Iterable[UUID],
        dependencies: Iterable[PlanDependency] = (),
        tasks: Iterable[Task],
        plan_id: UUID | None = None,
    ) -> Self:
        """Construct a canonical Plan and validate its exact Task bundle."""

        data: dict[str, object] = {
            "objective": objective,
            "assumptions": tuple(assumptions),
            "task_ids": tuple(task_ids),
            "dependencies": tuple(dependencies),
        }
        if plan_id is not None:
            data["plan_id"] = plan_id
        plan = cls.model_validate(data)
        plan.validate_tasks(tuple(tasks))
        return plan

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
            prerequisites[dependency.dependent_task_id].add(dependency.prerequisite_task_id)
        return tuple(
            task_id
            for task_id in self.task_ids
            if task_id not in completed and prerequisites[task_id].issubset(completed)
        )

    def _fingerprint_payload(self) -> dict[str, object]:
        return {
            "objective": self.objective.model_dump(mode="json"),
            "assumptions": [assumption.model_dump(mode="json") for assumption in self.assumptions],
            "task_ids": [str(task_id) for task_id in self.task_ids],
            "dependencies": [
                {
                    "prerequisite_task_id": str(dependency.prerequisite_task_id),
                    "dependent_task_id": str(dependency.dependent_task_id),
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

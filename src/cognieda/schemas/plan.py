"""Immutable Plan V1 coordination aggregate and structural validation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Iterable
from typing import Literal, Self
from uuid import UUID, uuid4

from pydantic import Field, NonNegativeInt, computed_field, field_validator, model_validator

from cognieda.schemas.artifacts import Assumption, Objective, Task
from cognieda.schemas.common import ImmutableCogniEDABaseModel
from cognieda.schemas.enums import PlanPriority

PlanContractVersion = Literal["plan/v1"]
PLAN_CONTRACT_VERSION: PlanContractVersion = "plan/v1"


class PlanTaskBinding(ImmutableCogniEDABaseModel):
    """Plan-specific coordination for one independent semantic Task FCO."""

    task_id: UUID
    order_rank: NonNegativeInt
    priority: PlanPriority = PlanPriority.NORMAL


class PlanDependency(ImmutableCogniEDABaseModel):
    """Directed prerequisite edge between two Tasks in one Plan."""

    prerequisite_task_id: UUID
    dependent_task_id: UUID

    @model_validator(mode="after")
    def _reject_self_dependency(self) -> PlanDependency:
        if self.prerequisite_task_id == self.dependent_task_id:
            raise ValueError("PlanDependency rejects a self dependency.")
        return self


class Plan(ImmutableCogniEDABaseModel):
    """Immutable, non-FCO plan over one exact Objective and a Task DAG."""

    plan_id: UUID = Field(default_factory=uuid4)
    objective: Objective
    assumptions: tuple[Assumption, ...] = ()
    task_bindings: tuple[PlanTaskBinding, ...] = ()
    dependencies: tuple[PlanDependency, ...] = ()
    contract_version: PlanContractVersion = PLAN_CONTRACT_VERSION

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

    @field_validator("task_bindings", mode="after")
    @classmethod
    def _canonicalize_bindings(
        cls,
        bindings: tuple[PlanTaskBinding, ...],
    ) -> tuple[PlanTaskBinding, ...]:
        task_ids = [binding.task_id for binding in bindings]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Plan rejects duplicate PlanTaskBinding task_id values.")
        return tuple(sorted(bindings, key=lambda item: (item.order_rank, str(item.task_id))))

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
        """Prove that supplied Task values exactly match this Plan's membership."""

        tasks_by_id: dict[UUID, Task] = {}
        for task in tasks:
            if task.task_id in tasks_by_id:
                raise ValueError("Plan rejects duplicate member Task identities.")
            tasks_by_id[task.task_id] = task

        if self.task_ids != set(tasks_by_id):
            raise ValueError("Plan Task inputs must exactly match binding membership.")

        for binding in self.task_bindings:
            task = tasks_by_id[binding.task_id]
            if task.objective_id != self.objective.objective_id:
                raise ValueError("Every bound Task must belong to the Plan Objective.")

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
        task_bindings: Iterable[PlanTaskBinding],
        dependencies: Iterable[PlanDependency] = (),
        tasks: Iterable[Task],
        plan_id: UUID | None = None,
    ) -> Self:
        """Construct a canonical Plan and validate its exact Task bundle."""

        data: dict[str, object] = {
            "objective": objective,
            "assumptions": tuple(assumptions),
            "task_bindings": tuple(task_bindings),
            "dependencies": tuple(dependencies),
        }
        if plan_id is not None:
            data["plan_id"] = plan_id
        plan = cls.model_validate(data)
        plan.validate_tasks(tuple(tasks))
        return plan

    @property
    def task_ids(self) -> frozenset[UUID]:
        """Derive Plan membership from the single binding source of truth."""

        return frozenset(binding.task_id for binding in self.task_bindings)

    def eligible_task_ids(
        self,
        *,
        completed_task_ids: Collection[UUID] = (),
    ) -> tuple[UUID, ...]:
        """Return uncompleted Tasks whose explicit prerequisites are complete."""

        completed = set(completed_task_ids)
        if completed.difference(self.task_ids):
            raise ValueError("Completed Task identity is outside Plan membership.")
        prerequisites = {task_id: set[UUID]() for task_id in self.task_ids}
        for dependency in self.dependencies:
            prerequisites[dependency.dependent_task_id].add(dependency.prerequisite_task_id)
        return tuple(
            binding.task_id
            for binding in self.task_bindings
            if binding.task_id not in completed
            and prerequisites[binding.task_id].issubset(completed)
        )

    def _fingerprint_payload(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "objective": self.objective.model_dump(mode="json"),
            "assumptions": [assumption.model_dump(mode="json") for assumption in self.assumptions],
            "task_bindings": [
                {
                    "task_id": str(binding.task_id),
                    "order_rank": binding.order_rank,
                    "priority": binding.priority.value,
                }
                for binding in self.task_bindings
            ],
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
        """Return the version-bound digest of canonical Plan semantics."""

        serialized = json.dumps(
            self._fingerprint_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(serialized).hexdigest()}"


__all__ = (
    "PLAN_CONTRACT_VERSION",
    "Plan",
    "PlanDependency",
    "PlanTaskBinding",
)

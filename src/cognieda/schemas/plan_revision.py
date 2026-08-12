"""Immutable PlanRevision V1 domain contracts and structural validation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Collection, Iterable
from typing import Literal, Self
from uuid import UUID, uuid4

from pydantic import (
    Field,
    NonNegativeInt,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)

from cognieda.execution.capabilities import Capability
from cognieda.schemas.artifacts import Task
from cognieda.schemas.common import ImmutableCogniEDABaseModel
from cognieda.schemas.enums import PlanPriority, TaskKind

PlanRevisionContractVersion = Literal["plan-revision/v1"]
PLAN_REVISION_CONTRACT_VERSION: PlanRevisionContractVersion = "plan-revision/v1"

_COMPATIBLE_CAPABILITIES: dict[TaskKind, frozenset[Capability]] = {
    TaskKind.DATA: frozenset(
        {
            Capability.DATA_ANALYSIS,
            Capability.DATA_PROFILING,
            Capability.DATA_TRANSFORMATION,
        }
    ),
    TaskKind.SCIENTIFIC: frozenset({Capability.HYPOTHESIS_TESTING}),
    TaskKind.GRAPH: frozenset({Capability.GRAPH_MINING}),
}


class PlanTaskBinding(ImmutableCogniEDABaseModel):
    """Revision-specific coordination and routing for one semantic Task."""

    task_id: UUID
    required_capability: Capability
    order_rank: NonNegativeInt
    priority: PlanPriority = PlanPriority.NORMAL


class PlanDependency(ImmutableCogniEDABaseModel):
    """Directed prerequisite edge between two Tasks in one PlanRevision."""

    prerequisite_task_id: UUID
    dependent_task_id: UUID

    @model_validator(mode="after")
    def _reject_self_dependency(self) -> PlanDependency:
        if self.prerequisite_task_id == self.dependent_task_id:
            raise ValueError("PlanDependency rejects a self dependency.")
        return self


class PlanRevision(ImmutableCogniEDABaseModel):
    """Immutable, non-FCO V1 snapshot of one Objective-scoped Task DAG."""

    plan_revision_id: UUID = Field(default_factory=uuid4)
    objective_id: UUID
    task_bindings: tuple[PlanTaskBinding, ...] = ()
    dependencies: tuple[PlanDependency, ...] = ()
    contract_version: PlanRevisionContractVersion = PLAN_REVISION_CONTRACT_VERSION

    @field_validator("task_bindings", mode="after")
    @classmethod
    def _canonicalize_bindings(
        cls,
        bindings: tuple[PlanTaskBinding, ...],
    ) -> tuple[PlanTaskBinding, ...]:
        task_ids = [binding.task_id for binding in bindings]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("PlanRevision rejects duplicate PlanTaskBinding task_id values.")
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
            raise ValueError("PlanRevision rejects duplicate dependency edges.")
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
    def _validate_against_authoritative_tasks(self, info: ValidationInfo) -> PlanRevision:
        tasks = self._authoritative_tasks(info)
        tasks_by_id: dict[UUID, Task] = {}
        for task in tasks:
            if task.task_id in tasks_by_id:
                raise ValueError("PlanRevision rejects duplicate authoritative Task IDs.")
            tasks_by_id[task.task_id] = task

        member_ids = {binding.task_id for binding in self.task_bindings}
        missing_ids = member_ids.difference(tasks_by_id)
        if missing_ids:
            raise ValueError("PlanRevision rejects a binding without an authoritative Task.")

        for binding in self.task_bindings:
            task = tasks_by_id[binding.task_id]
            if task.objective_id != self.objective_id:
                raise ValueError("Every bound Task must belong to the PlanRevision Objective.")
            self._validate_binding_compatibility(task, binding)

        self._validate_dependency_graph(member_ids)
        return self

    @staticmethod
    def _authoritative_tasks(info: ValidationInfo) -> tuple[Task, ...]:
        context = info.context
        if not isinstance(context, dict):
            raise ValueError(
                "PlanRevision requires authoritative Tasks through PlanRevision.create()."
            )
        tasks = context.get("authoritative_tasks")
        if not isinstance(tasks, tuple) or not all(isinstance(task, Task) for task in tasks):
            raise ValueError(
                "PlanRevision requires authoritative Tasks through PlanRevision.create()."
            )
        return tasks

    @staticmethod
    def _validate_binding_compatibility(task: Task, binding: PlanTaskBinding) -> None:
        capabilities = _COMPATIBLE_CAPABILITIES[task.kind]
        if binding.required_capability not in capabilities:
            raise ValueError(f"{task.kind.name} Task has an incompatible required capability.")

    def _validate_dependency_graph(self, member_ids: set[UUID]) -> None:
        in_degree = dict.fromkeys(member_ids, 0)
        dependents = {task_id: set[UUID]() for task_id in member_ids}
        for dependency in self.dependencies:
            if (
                dependency.prerequisite_task_id not in member_ids
                or dependency.dependent_task_id not in member_ids
            ):
                raise ValueError("PlanRevision rejects a dependency endpoint outside membership.")
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
            raise ValueError("PlanRevision dependencies must form an acyclic graph.")

    @classmethod
    def create(
        cls,
        *,
        objective_id: UUID,
        task_bindings: Iterable[PlanTaskBinding],
        dependencies: Iterable[PlanDependency] = (),
        authoritative_tasks: Iterable[Task],
        plan_revision_id: UUID | None = None,
    ) -> Self:
        """Validate and construct a revision against authoritative Task objects."""

        data: dict[str, object] = {
            "objective_id": objective_id,
            "task_bindings": tuple(task_bindings),
            "dependencies": tuple(dependencies),
        }
        if plan_revision_id is not None:
            data["plan_revision_id"] = plan_revision_id
        tasks = tuple(authoritative_tasks)
        return cls.model_validate(data, context={"authoritative_tasks": tasks})

    @property
    def task_ids(self) -> frozenset[UUID]:
        """Derive revision membership from the single binding source of truth."""

        return frozenset(binding.task_id for binding in self.task_bindings)

    def eligible_task_ids(
        self,
        *,
        completed_task_ids: Collection[UUID] = (),
    ) -> tuple[UUID, ...]:
        """Return uncompleted Tasks whose explicit prerequisites are complete."""

        completed = set(completed_task_ids)
        unknown = completed.difference(self.task_ids)
        if unknown:
            raise ValueError("Completed Task identity is outside PlanRevision membership.")
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
            "objective_id": str(self.objective_id),
            "task_bindings": [
                {
                    "task_id": str(binding.task_id),
                    "required_capability": binding.required_capability.value,
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
        """Return the sha256 digest of structurally canonical plan content."""

        serialized = json.dumps(
            self._fingerprint_payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(serialized).hexdigest()}"


__all__ = (
    "PLAN_REVISION_CONTRACT_VERSION",
    "PlanDependency",
    "PlanRevision",
    "PlanTaskBinding",
)

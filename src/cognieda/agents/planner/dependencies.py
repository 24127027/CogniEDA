from dataclasses import dataclass


@dataclass(frozen=True)
class PlannerDeps:
    """Governed dependencies available to Planner tools at runtime."""


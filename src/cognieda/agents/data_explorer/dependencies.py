"""DEDependencies — Research context injected into DE tools via RunContext.

This module defines the dependency type passed to every Pydantic AI tool call
during a Data Explorer agent run.  Tools that need awareness of the research
context (DataProfile schema, Objective intent) receive this via RunContext.

Usage in a toolset:
    @toolset.tool                              # not tool_plain — needs RunContext
    def some_tool(ctx: RunContext[DEDependencies], ...) -> dict:
        profile = ctx.deps.data_profile        # may be None on profiling pass
        objective = ctx.deps.objective         # may be None when no Objective set

Design notes:
- DEDependencies is a plain dataclass (Pydantic AI's recommended pattern).
- DataProfile and Objective are typed as Any to avoid circular imports with
  cognieda.schemas.artifacts.  At runtime they carry the real objects.
- objective is optional: Data profiling tasks may run before an Objective exists.
- data_profile is optional: on the profiling pass it is None by definition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DEDependencies:
    """Research context injected into Data Explorer tools via RunContext.

    Attributes:
        data_profile: The authoritative DataProfile for the current dataset,
            or None when the task IS the profiling request.  Tools can use
            this to validate column names before attempting operations.
        objective: The Objective that scopes this analysis, or None when
            running a standalone / un-scoped profiling task.  Tools should
            treat this as guidance only — never as a reasoning premise.
        column_names: Convenience list of column names extracted from
            data_profile (empty when data_profile is None).  Tools can use
            this without unpacking the full profile object.
    """

    data_profile: Any | None = field(default=None)  # DataProfile at runtime
    objective: Any | None = field(default=None)      # Objective at runtime

    @property
    def column_names(self) -> list[str]:
        """Return column names from the DataProfile, or [] if not available."""
        if self.data_profile is None:
            return []
        cols = getattr(self.data_profile, "columns", ())
        return [getattr(c, "name", str(c)) for c in cols]

    @property
    def numeric_column_names(self) -> list[str]:
        """Return only continuous (numeric) column names from the DataProfile."""
        if self.data_profile is None:
            return []
        cols = getattr(self.data_profile, "columns", ())
        return [
            getattr(c, "name", str(c))
            for c in cols
            if str(getattr(c, "variable_type", "")) == "continuous"
        ]


__all__ = ("DEDependencies",)

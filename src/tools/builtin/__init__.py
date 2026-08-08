from collections.abc import Callable
from enum import Enum, member
from typing import Any, cast

from .dataset import create_dataset_toolset
from .graph import create_graph_toolset

BuiltinTool = Callable[..., Any]


class AvailableBuiltinTools(Enum):
    DATASET = member(create_dataset_toolset)
    GRAPH = member(create_graph_toolset)

    @property
    def function(self) -> BuiltinTool:
        """Return the callable represented by this built-in tool member."""
        return cast(BuiltinTool, self.value)


__all__ = (
    "AvailableBuiltinTools",
    "BuiltinTool",
    "create_dataset_toolset",
    "create_graph_toolset",
)

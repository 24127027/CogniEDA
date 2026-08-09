from collections.abc import Callable
from enum import Enum, member
from typing import Any, cast

from ..delegation.dataset import invoke_data_capability
from .dataset import create_dataset_toolset
from .graph import create_graph_toolset
from .terminal import print_to_terminal

BuiltinTool = Callable[..., Any]


class AvailableBuiltinTools(Enum):
    DATASET = member(create_dataset_toolset)
    GRAPH = member(create_graph_toolset)
    TERMINAL = member(print_to_terminal)
    DATA_DELEGATION = member(invoke_data_capability)

    @property
    def function(self) -> BuiltinTool:
        """Return the callable represented by this built-in tool member."""
        return cast(BuiltinTool, self.value)


__all__ = (
    "AvailableBuiltinTools",
    "BuiltinTool",
    "create_dataset_toolset",
    "create_graph_toolset",
    "invoke_data_capability",
)

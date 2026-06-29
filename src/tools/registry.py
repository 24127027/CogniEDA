from collections.abc import Callable

from pydantic_ai import FunctionToolset


class ToolRegistry:
    def create_toolset(
        self,
        tools: list[Callable],
    ) -> FunctionToolset:
        return FunctionToolset(tools)


registry = ToolRegistry()
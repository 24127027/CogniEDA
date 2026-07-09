from collections.abc import Callable
from types import SimpleNamespace

from langgraph.graph.state import StateNode  # type: ignore[attr-defined]
from pydantic import BaseModel


class NodeRegistry[StateT: BaseModel, ContextT: BaseModel | None]:
    """
    A registry for LangGraph nodes, allowing for automatic registration of node functions.

    How to use:
        In nodes.py:
            from ..utilities.nodes_registry import NodeRegistry
            registry = NodeRegistry[State, Context]()
            R = registry.R  # Shortcut export for graph.py to use dot-notation

            @registry.register()
            def my_node(state: State, runtime: Runtime[Context]):
                pass

        In graph.py:
            from .nodes import reg, R
            import nodes # Triggers the decorators to run

            for node_name, node_func in reg.nodes.items():
                builder.add_node(node_name, node_func)

            builder.add_edge(START, R.my_node)
    """

    def __init__(self) -> None:
        self._registry: dict[str, StateNode[StateT, ContextT]] = {}
        self.R = SimpleNamespace()

    def register(
        self,
        name: str | None = None,
    ):
        """Decorator to automatically register LangGraph nodes."""

        def decorator(func: StateNode[StateT, ContextT]) -> StateNode[StateT, ContextT]:
            fallback_name = getattr(func, "__name__", type(func).__name__)
            node_name = name if name else fallback_name

            if node_name in self._registry:
                raise ValueError(f"Duplicate node name registered: '{node_name}'")

            self._registry[node_name] = func
            setattr(self.R, node_name, node_name)
            return func

        return decorator

    @property
    def nodes(self):
        """Returns the dictionary mapping string names to functions for graph.add_node()."""
        return dict(self._registry)

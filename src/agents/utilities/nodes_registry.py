from typing import Dict, TypeVar, Generic
from types import SimpleNamespace
from langgraph.graph.state import StateNode

from ..types import BaseState

StateT = TypeVar("StateT", bound=BaseState)

class NodeRegistry(Generic[StateT]):
    """
    A registry for LangGraph nodes, allowing for automatic registration of node functions.
    How to use:
        In nodes.py:
            from ..utilities.nodes_registry import NodeRegistry
            registry = NodeRegistry[PlannerState]()  # Specify the state type for type checking
            R = registry.R  # Shortcut export for graph.py to use dot-notation

            @registry.register()
            def my_node(state: PlannerState):
                pass
        
        In graph.py:
            from .nodes import reg, R
            import nodes # Triggers the decorators to run

            for node_name, node_func in reg.nodes.items():
                builder.add_node(node_name, node_func)

            builder.add_edge(START, R.my_node)
    """

    def __init__(self):
        self._registry: dict[str, StateNode[StateT, None]] = {}
        self.R = SimpleNamespace()

    def register(self, name: str | None = None):
        """Decorator to automatically register LangGraph nodes."""
        def decorator(func: StateNode[StateT, None]):
            node_name = name if name else func.__name__ #type: ignore
            
            if node_name in self._registry:
                raise ValueError(f"Duplicate node name registered: '{node_name}'")
                
            self._registry[node_name] = func
            setattr(self.R, node_name, node_name)
            return func
        return decorator

    @property
    def nodes(self) -> Dict[str, StateNode[StateT, None]]:
        """Returns the dictionary mapping string names to functions for graph.add_node()."""
        return dict(self._registry)
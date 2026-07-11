from enum import Enum

from .dataset import create_dataset_toolset
from .graph import create_graph_toolset


class AvailableBuiltinTools(Enum):
    DATASET = create_dataset_toolset
    GRAPH = create_graph_toolset
    
__all__ = ["AvailableBuiltinTools"]
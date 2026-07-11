

from pydantic_ai.tools import RunContext
from ..dependencies.protocols import HasDatasetRepository

def create_dataset_toolset(ctx: RunContext[HasDatasetRepository]) -> dict:
    """
    Dummy builtin dataset tool for testing purposes.
    """
    ...


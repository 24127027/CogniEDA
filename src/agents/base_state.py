from pydantic import BaseModel

class BaseState(BaseModel):
    """
    Base class for all states in the agent graph.
    This class is intended to be subclassed by specific state implementations.
    """

    ...
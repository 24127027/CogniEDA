from pydantic import BaseModel
from typing import Any

class AgentRequest(BaseModel):
    """
    Input model for the agent.
    """
    context: str
    user_query: str

class AgentResult(BaseModel):
    """
    Output model for the agent.
    """
    payload: Any
    


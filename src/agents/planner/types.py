from ..types import AgentRequest, AgentResult, BaseState

class PlannerRequest(AgentRequest):
    """
    Represents a request to the Planner agent.
    This class can be extended to include specific fields required for planning tasks.
    """
    pass

class PlannerResult(AgentResult):
    """
    Represents the result from the Planner agent.
    This class can be extended to include specific fields that represent the outcome of planning tasks.
    """
    pass

class PlannerState(BaseState):
    """
    Represents the state of the Planner agent.
    This class can be extended to include specific fields that represent the internal state of the planner.
    """
    pass
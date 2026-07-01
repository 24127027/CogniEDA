from .types import PlannerState
from ..utilities.nodes_registry import NodeRegistry

registry = NodeRegistry[PlannerState]()
R = registry.R

# --------------------
# Core
# --------------------

@registry.register()
def understand_request(state: PlannerState):
    """
    LLM interprets the user's latest message.

    The model identifies the user's intent and extracts any information
    needed for subsequent planning. This step intentionally does not
    consume Session Frame context so intent recognition is based solely
    on the user's request.
    """


@registry.register()
def route_intent(state: PlannerState) -> str:
    """Route the user's intent to the appropriate node and return a routing key."""
    raise NotImplementedError(
        "route_intent must return one of: answer, suggest, manage_task, execute, objective, assumption."
    )


# --------------------
# Question answering
# --------------------

@registry.register()
def answer_question(state: PlannerState):
    """LLM answers the user's question
        The LLM is provided with context from the session, so it can answer the question more accurately.
    """
    pass


# --------------------
# Research planning
# --------------------

@registry.register()
def propose_questions(state: PlannerState):
    """
    LLM proposes possible research directions, open questions, or
    investigation ideas based on the current research context.
    """
    pass


@registry.register()
def expand_plan(state: PlannerState):
    """
    LLM expands an approved research direction into executable Tasks.

    This may include refining scope, decomposing large Tasks into
    subtasks, identifying dependencies, and determining a concrete
    execution plan.
    """
    pass


# --------------------
# Task management
# --------------------

@registry.register()
def manage_tasks(state: PlannerState):
    """
    Apply user-authorized modifications to the Task hierarchy.

    Supported operations include creating, updating, deleting,
    and changing Task state.

    Should produce operations that later apply to the Task hierarchy, but does not directly modify it.
    """
    pass


@registry.register()
def select_task(state: PlannerState):
    """
    Determine which task to execute 
    Planner resolves which Task object this refers to.
    """
    pass


# --------------------
# Execution
# --------------------

@registry.register()
def prepare_execution(state: PlannerState):
    """ 
    Choose the appropriate executor for the task and prepare the execution context.
    """
    pass


@registry.register()
def dispatch_executor(state: PlannerState):
    """Delegate to another specialist agent."""
    pass

@registry.register()
def review_execution(state: PlannerState):
    """Review the results of the execution and update the state accordingly."""
    pass


# --------------------
# Knowledge management
# --------------------

@registry.register()
def review_conflicts(state: PlannerState):
    """Determine whether new results contradict existing knowledge
    and prepare user review.
    """
    pass

@registry.register()
def manage_objective(state: PlannerState):
    """Apply changes to the objective, such as updating, refining, or clarifying it."""
    pass

@registry.register()
def manage_assumptions(state: PlannerState):
    """Apply changes to the assumptions, such as updating, refining, or clarifying them."""
    pass


# --------------------
# User interaction
# --------------------

@registry.register()
def request_user_input(state: PlannerState):
    """Prepare a request for user input, such as a question or clarification, and present it to the user."""
    pass

@registry.register()
def pause(state: PlannerState):
    """Pause the current process and wait for user input or confirmation before proceeding."""

    pass

@registry.register()
def process_decision(state: PlannerState) -> str:
    """Interpret the user's response after a pause and return a routing key for the planner."""
    raise NotImplementedError(
        "process_decision must return one of: clarify, approved_questions, approved_task, approved_plan, approved_conflict, approved_execution, cancel."
    )


# --------------------
# Finalization
# --------------------

@registry.register()
def commit(state: PlannerState):
    """
    Atomically persist all planner state changes.

    This includes updating Tasks, Objectives, Assumptions, Session Frame,
    and any other modified planner state before ending the iteration.
    """
    pass

from langgraph.graph import END
from langgraph.runtime import Runtime
from pydantic_ai.messages import ToolReturn
from cognieda.schemas.artifacts import DataProfile, Evidence

from .state import State
from .context import Context

async def planning(state: State, runtime: Runtime[Context]) -> State:
    """Planning node of the DataExplorer agent's internal workflow."""
    # When tracking back to planning, drop the evidence/dataprofile generated at execute node
    # as they did not successfully answer the request.
    state["artifacts"] = []
    
    prompt = (
        f"Analyze the following request and create a step-by-step plan to solve it.\n\n"
        f"Context: {state.get('external_context')}\n"
        f"Task: {state.get('input')}"
    )
    
    if state.get("feedback"):
        prompt += (
            f"\n\nIMPORTANT: Your previous plan failed. Here is the feedback from the evaluation: "
            f"'{state['feedback']}'. Please revise your plan to address these issues."
        )
    
    result = await runtime.context.agent.run(
        prompt,
        deps=runtime.context.deps,
        message_history=state.get("messages", [])
    )
    
    return {
        **state,
        "messages": result.all_messages(),
    }

async def execute(state: State, runtime: Runtime[Context]) -> State:
    """Execute node of the DataExplorer agent's internal workflow."""
    prompt = "Now execute the plan you just created. Use your built-in tools as necessary."
    
    result = await runtime.context.agent.run(
        prompt,
        deps=runtime.context.deps,
        message_history=state.get("messages", [])
    )
    
    artifacts = state.get("artifacts", [])
    if artifacts is None:
        artifacts = []
        
    for msg in result.new_messages():
        if isinstance(msg, ToolReturn):
            if isinstance(msg.content, (DataProfile, Evidence)):
                artifact = msg.content
                
                # We need to fill in semantic_description for DataProfile which is generated blank by the tool.
                if isinstance(artifact, DataProfile):
                    from pydantic import BaseModel
                    from pydantic_ai import Agent
                    
                    class SemanticDescriptions(BaseModel):
                        descriptions: dict[str, str]
                        
                    desc_prompt = (
                        f"Based on the following DataProfile schema, generate a short, concise "
                        f"semantic description for each column explaining what it likely represents.\n\n"
                        f"{artifact.model_dump_json()}"
                    )
                    
                    # Create a temporary agent bound to the same model to force the structured output
                    desc_agent = Agent(
                        runtime.context.agent.model,
                        result_type=SemanticDescriptions
                    )
                    
                    desc_result = await desc_agent.run(desc_prompt)
                    
                    # Use the artifact's built-in method to safely hardcode the descriptions
                    artifact = artifact.with_column_descriptions(desc_result.data.descriptions)
                    
                artifacts.append(artifact)
                
    return {
        **state,
        "artifacts": artifacts,
        "messages": result.all_messages(),
    }

async def check_result(state: State, runtime: Runtime[Context]) -> State:
    """Check result node of the DataExplorer agent's internal workflow."""
    prompt = (
        "Review the actions you have taken and the artifacts generated. "
        "Did you successfully and fully complete the original task? "
        "If you succeeded, reply with ONLY the word 'YES'. "
        "If you failed or the output is incomplete, reply with 'NO: ' followed by a detailed reason "
        "explaining why it failed and what needs to be done differently."
    )
    
    result = await runtime.context.agent.run(
        prompt,
        deps=runtime.context.deps,
        message_history=state.get("messages", [])
    )
    
    feedback = result.data.strip()
    
    return {
        **state,
        "messages": result.all_messages(),
        "feedback": feedback,
    }

def _route_after_check_result(state: State) -> str:
    """Determine the next node after check_result based on the state."""
    feedback = state.get("feedback", "")
    if feedback.upper().startswith("YES"):
        return END
    return "planning"
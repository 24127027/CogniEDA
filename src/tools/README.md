# Tools Directory Guide

This directory houses the core logic for managing and providing tools to various agents within CogniEDA. It distinguishes between **built-in tools**, which are Python functions directly integrated into the application, and **MCP (Model Context Protocol) servers**, which are external services exposed as toolsets.

## Built-in Tools

Built-in tools are Python functions designed to perform specific tasks within the CogniEDA application. They are directly callable by agents.

### Implementation

To implement a built-in tool, simply define a Python function. For example, a tool to search the graph might look like this (as hinted in `manager.py`):

```python
# src/tools/builtin/graph.py
def search_graph(query: str) -> dict:
    """Searches the knowledge graph for relevant information.""""
    # ... implementation details ...
    return {"results": []}
```

### Registration

Built-in tools need to be registered with the `registry` to be discoverable and usable by the `ToolManager`. The `registry` (defined in `src/tools/registry.py`) is responsible for converting these functions into `FunctionToolset` objects.

```python
# src/tools/registry.py (conceptual example)
from pydantic_ai import FunctionToolset

class ToolRegistry:
    def __init__(self):
        self._tools = {}

    def register(self, func):
        self._tools[func.__name__] = func

    def create_toolset(self, funcs: list) -> FunctionToolset:
        # Logic to create a FunctionToolset from a list of functions
        pass

registry = ToolRegistry()

# Example of registering a tool
# registry.register(search_graph)
```

### Association with Workers

Once implemented and registered, built-in tools are associated with specific agents (workers) via the `WORKER_BUILTIN_TOOLS` dictionary in `src/tools/manager.py`.

```python
# src/tools/manager.py
WORKER_BUILTIN_TOOLS = {
    "planner": [
        # search_graph,
        # create_task,
        # update_session_frame,
    ],
    "graph_miner": [
        # search_graph,
    ],
    "hypothesis_analyst": [
        # run_pearson,
        # run_ttest,
    ],
}
```

To enable a built-in tool for an agent, uncomment or add the tool's function reference to the corresponding worker's list.

## MCP (Model Context Protocol) Servers

MCP servers represent external services that expose their functionalities as toolsets to CogniEDA agents. These are configured externally and loaded by the `ToolManager`.

### Configuration (`config/mcp.toml`)

MCP servers are defined in `config/mcp.toml`. This file specifies the details for connecting to each MCP server.

```toml
# config/mcp.toml (example)
[filesystem]
url = "http://localhost:8000/filesystem"

[neo4j]
url = "http://localhost:8001/neo4j"
```

Each section (e.g., `[filesystem]`, `[neo4j]`) defines a named MCP server with its `url`.

### Loading

The `ToolManager` uses `src/tools/mcp/loader.py` to load these configurations and create `MCPToolset` objects. The `load_mcp_toolsets` function reads `mcp.toml` and initializes the necessary MCP toolsets.

### Association with Workers (`config/agents.toml`)

Agents are configured to use specific MCP servers via the `config/agents.toml` file.

```toml
# config/agents.toml (example)
[planner]
mcp = [
    "filesystem",
    "neo4j",
]

[graph_miner]
mcp = [
    "neo4j",
]
```

Under each worker's section (e.g., `[planner]`), the `mcp` key lists the names of the MCP servers (as defined in `mcp.toml`) that the worker should have access to.

## Using Toolsets with Agents

The `ToolManager` (instantiated as `tool_manager` in `src/tools/manager.py`) is responsible for providing the correct toolsets to each agent. The `create_agent` function in `src/agents/llm.py` demonstrates how an agent receives its toolsets:

```python
# src/agents/llm.py
from tools.manager import tool_manager

def create_agent(worker: str, config: ModelConfig) -> Agent:
    # ... model initialization ...
    
    return Agent(
        model=model,
        toolsets=tool_manager.toolsets_for(worker), # Toolsets are provided here
    )
```

When an agent is created, `tool_manager.toolsets_for(worker)` gathers all associated built-in and MCP toolsets, making them available for the agent to use during its operation.

## Project Initialization

To ensure `registry` and `tool_manager` are properly initialized when the project starts, a dedicated initialization function should be called. This function, `initialize_tool_manager`, is responsible for setting up the `ToolManager` instance with the correct configurations and the `ToolRegistry`.

```python
# src/tools/manager.py

# ... (existing imports and WORKER_BUILTIN_TOOLS) ...

tool_manager: ToolManager | None = None

def initialize_tool_manager(
    path: str | Path = "config/agents.toml",
    mcp_path: str | Path = "config/mcp.toml",
) -> None:
    global tool_manager
    tool_manager = ToolManager.from_config_path(path=path, mcp_path=mcp_path)

This `initialize_tool_manager` function should be called once at the application's startup, for example, in your main application entry point or a dedicated setup module.

Additionally, in `src/agents/llm.py`, the `create_agent` function should ensure that `tool_manager` has been initialized before attempting to use it:

```python
# src/agents/llm.py
from tools import manager as tools_manager

# ... (existing ModelConfig and other code) ...

def create_agent(worker: str, config: ModelConfig) -> Agent:
    if tools_manager.tool_manager is None:
        tools_manager.initialize_tool_manager()

    return Agent(
        model=model,
        toolsets=tools_manager.tool_manager.toolsets_for(worker),
    )

This pattern ensures that `tool_manager` is always available and correctly configured when an agent needs to access its toolsets.
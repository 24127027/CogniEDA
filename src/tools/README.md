# Tools

This package manages the capabilities available to LLM agents.

CogniEDA supports three capability types:

- **Built-in tools** — Python functions implemented inside the application.
- **Skills** — File-based instructions loaded as agent capabilities.
- **MCP servers** — External tools provided through the Model Context Protocol (MCP).

The `ToolManager` assembles these capabilities when an agent is created. Skills and MCP
toolsets come from configuration; each agent class selects its own built-in tools.

## Built-in Tools

### Current implementation

Built-in tools are regular Python functions exposed through `AvailableBuiltinTools`. An agent
class owns its selection and passes that sequence to `create_agent()`.

```text
src/tools/
|-- builtin_tools/
|   |-- __init__.py
|   |-- dataset.py
|   `-- graph.py
`-- manager.py
```

To add a built-in tool:

1. Implement the function under `src/tools/builtin_tools/`.
2. Add it to `AvailableBuiltinTools` in `src/tools/builtin_tools/__init__.py`.
3. Include the enum member in each agent class that needs the tool.

Example:

```python
from tools.builtin_tools import AvailableBuiltinTools

class Planner:
    builtin_tools = (AvailableBuiltinTools.GRAPH,)

    def create_llm_agent(self, config: ModelConfig) -> Agent[PlannerDeps]:
        return create_agent(
            worker="planner",
            config=config,
            deps_type=PlannerDeps,
            builtin_tools=self.builtin_tools,
        )
```

`create_agent()` forwards the selection to `ToolManager`. The manager resolves the enum members,
wraps the complete callable sequence in one `FunctionToolset`, and combines it with the worker's
configured MCP toolsets. The manager does not decide which worker receives which built-in tool.

### Not yet implemented

The exported graph and dataset callables are placeholder tools. Their repository-backed
analytical behavior is not implemented yet. The current Planner and Executor wrappers define
their built-in selections but do not create Pydantic AI agents yet; the example above documents
the intended call pattern for that integration.

## Skills

Skills provide reusable instructions and domain knowledge. Configure available skills in
`config/skills.toml`.

Each entry points to one or more directories containing `SKILL.md` files. Assign configured
skills to workers in `config/agents.toml`:

```toml
[planner]
skills = [
    "memory_management",
    "task_planning",
]
```

## MCP Servers

Configure available MCP servers in `config/mcp.toml`:

```toml
[filesystem]
transport = "stdio"
command = "uvx"
args = ["mcp-server-filesystem"]

[neo4j]
transport = "http"
url = "http://localhost:8000/mcp"
```

Assign configured MCP servers to workers in `config/agents.toml`:

```toml
[planner]
mcp = ["filesystem"]
```

The repository's current `config/mcp.toml` contains commented examples only. A worker that
names an MCP server in `config/agents.toml` cannot assemble that MCP toolset until the matching
server definition is enabled.

## Worker Assembly

When an agent is created, `ToolManager` combines:

1. The built-in enum members supplied by the calling agent class.
2. MCP toolsets named by that worker in `config/agents.toml`.
3. Skills named by that worker in `config/agents.toml`.

Unknown workers and references to undefined MCP servers are rejected explicitly.

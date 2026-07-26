# Tools

> **Role:** Package technical reference. **Canonical concept owner:**
> [Product surface and bootstrap boundary](../../docs/product-surface-and-bootstrap-boundary.md).
> **Contributor entry:** [Contributor documentation](../../docs/development/index.md).
> **Current-state owner:** [CogniEDA current state](../../docs/current-state.md).

This package manages the capabilities available to LLM agents.

CogniEDA supports three capability types:

- **Built-in tools** — Python functions implemented inside the application.
- **Skills** — File-based instructions loaded as agent capabilities.
- **MCP servers** — External tools provided through the Model Context Protocol (MCP).

The `ToolManager` assembles these capabilities when an agent is created. Skills and MCP
toolsets come from configuration; each agent class selects its own built-in tools.

## Built-in Tools

### Current implementation

Built-in tools are regular Python functions exposed through
`AvailableBuiltinTools`. `create_agent()` accepts an explicit sequence and
passes it to `ToolManager`, but current configured Planner model adapters pass
an empty sequence. The Planner wrapper and Graph Miner stub declare a graph
selection without wiring it into those configured adapters. The exported graph
and dataset functions are placeholders, so no current production path provides
repository-backed built-in analytical tools.

```text
src/tools/
|-- builtin_tools/
|   |-- __init__.py
|   |-- dataset.py
|   `-- graph.py
`-- manager.py
```

The intended integration pattern is:

1. Implement the function under `src/tools/builtin_tools/`.
2. Add it to `AvailableBuiltinTools` in `src/tools/builtin_tools/__init__.py`.
3. Include the enum member in each agent class that needs the tool.

Example:

```python
from tools.builtin_tools import AvailableBuiltinTools

agent = create_agent(
    worker="planner",
    config=config,
    deps_type=PlannerDeps,
    builtin_tools=(AvailableBuiltinTools.GRAPH,),
)
```

`create_agent()` forwards the caller's selection to `ToolManager`. The manager
resolves the enum members, wraps the callable sequence in one
`FunctionToolset`, and combines it with the worker's configured MCP toolsets.
The manager does not decide which worker receives which built-in tool.

### Not yet implemented

Repository-backed graph and dataset behavior is not implemented. Planner nodes
do create PydanticAI agents for configured request understanding,
decomposition, Task management, and Objective management, but they currently
pass no built-ins. The protected Hypothesis Analyst constructs a separate
no-tool PydanticAI agent, and the Data Explorer uses its role-specific
registry/dispatcher boundary rather than `ToolManager`. Graph Miner remains an
unregistered stub.

## Skills

Skills provide reusable instructions and domain knowledge. Configure available skills in
`config/skills.toml`.

The checked-in skill configuration names directories that are absent from the
tracked `skills/` tree. The loader can construct capability objects from the
configuration, but no tracked runtime `SKILL.md` content exists for those
entries.

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

The repository's current `config/mcp.toml` contains commented examples only.
`config/agents.toml` nevertheless names `filesystem` and `neo4j`. A configured
agent that requests either server fails explicitly until a matching definition
is supplied.

## Worker Assembly

When `agents.llm.create_agent()` is used, `ToolManager` supplies:

1. The built-in enum members supplied by the calling agent class.
2. MCP toolsets named by that worker in `config/agents.toml`.
3. Skills named by that worker in `config/agents.toml`.

`create_agent()` separately passes the configured skill capabilities to
PydanticAI. Unknown workers and references to undefined MCP servers are
rejected explicitly. The checked-in configuration currently exercises that
undefined-MCP failure unless a deployment replaces or enables the referenced
servers.

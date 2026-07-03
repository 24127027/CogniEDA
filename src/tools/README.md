# Tools

This package manages the capabilities available to LLM agents.

CogniEDA supports three capability types:

- **Built-in tools** — Python functions implemented inside the application.
- **Skills** — File-based instructions loaded as agent capabilities.
- **MCP servers** — External tools provided through the Model Context Protocol (MCP).

The `ToolManager` loads these capabilities from configuration files and provides them when an agent is created.

## Built-in Tools

Built-in tools are regular Python functions.

```
src/tools/
├── builtin/
├── registry.py
└── manager.py
```

To add a built-in tool:

1. Implement the function under `src/tools/builtin/`.
2. Assign the function to one or more workers in `WORKER_BUILTIN_TOOLS` in `manager.py`.

Example:

```python
from .builtin.graph import search_graph

WORKER_BUILTIN_TOOLS = {
    "planner": [
        search_graph,
    ],
}
```

## Skills

Skills provide reusable instructions and domain knowledge.

Configure available skills in:

```
config/skills.toml
```

Each entry points to one or more directories containing `SKILL.md` files.

Example:

```
skills/
└── statistics/
    └── hypothesis-testing/
        └── SKILL.md
```

Assign skills to workers in:

```toml
# config/agents.toml

[planner]
skills = [
    "memory_management",
    "task_planning",
]
```

## MCP Servers

Configure available MCP servers in:

```
config/mcp.toml
```

Example:

```toml
[filesystem]
transport = "stdio"
command = "uvx"
args = ["mcp-server-filesystem"]

[neo4j]
transport = "http"
url = "http://localhost:8000/mcp"
```

Assign MCP servers to workers in:

```toml
[planner]
mcp = [
    "filesystem",
    "neo4j",
]
```

## Worker Configuration

Each worker declares the capabilities it receives in `config/agents.toml`.

```toml
[planner]
skills = ["task_planning"]
mcp = ["filesystem"]
```

When an agent is created, the `ToolManager` automatically assembles the configured built-in tools, skills, and MCP toolsets for that worker.
# Configuration Files

This directory contains configuration contracts and checked-in example
configuration for CogniEDA agents, skills, and Model Context Protocol (MCP)
servers.

## Current implementation status

The checked-in configuration is not a runnable deployment configuration.
`agents.toml` references `filesystem` and `neo4j`, while their definitions in
`mcp.toml` are commented examples. `skills.toml` references directories under
`skills/`, but no tracked `SKILL.md` definitions currently exist there.
`ToolManager` fails explicitly when an agent requests an undefined MCP server.
A deployment or test must supply a coherent replacement before model-backed
configured agents are runnable.

## `agents.toml`

This file defines which MCP toolsets are associated with each agent (worker).

**Example:**
```toml
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
In this example:
- The `planner` agent has access to the `filesystem` and `neo4j` MCP servers.
- The `graph_miner` agent has access to the `neo4j` MCP server.

## `mcp.toml`

This file is the loader input for MCP connection details. In the checked-in
file, every server block is commented and therefore no MCP toolset is defined.
The following is an activation example, not current supported configuration.

**Example:**
```toml
[filesystem]
transport = "stdio"
command = "uvx"
args = ["mcp-server-filesystem"]

[neo4j]
transport = "http"
url = "http://localhost:8000/mcp"
```
In this example:
- The `filesystem` MCP server is configured to use `stdio` transport, executing a local command.
- The `neo4j` MCP server is configured to use `http` transport, connecting to a specified URL.

## `skills.toml`

This file defines `SkillsCapability` configuration. Its current directory
entries are placeholders until matching tracked skill definitions or
deployment-supplied directories exist.

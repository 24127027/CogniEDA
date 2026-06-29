# Configuration Files

This directory contains configuration files for CogniEDA agents and Model Context Protocol (MCP) servers.

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

This file configures the connection details for various MCP (Model Context Protocol) servers. These servers expose external functionalities as toolsets to CogniEDA agents.

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

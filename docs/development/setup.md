# Development Setup

## Prerequisites

- Python 3.12+
- `uv`

## Install

From the repository root:

```powershell
uv sync
uv tool install --editable .
copy .env.example .env
```

If uv's tool binary directory is not on `PATH`, run:

```powershell
uv tool update-shell
```

Then open a new shell. The editable tool installation does not require
activation of the project `.venv`, and Python source edits are visible to the
installed command without reinstalling. Refresh or reinstall the tool when
project dependency metadata changes.

## Environment

Current `.env.example` contains:

```text
COGNIEDA_ENV=local
COGNIEDA_LOG_LEVEL=INFO
COGNIEDA_DB_URL=
COGNIEDA_DB_ECHO=false
```

Database behavior:

- If `COGNIEDA_DB_URL` is empty, the default SQLite URL points to `.local/cognieda_graph.sqlite3`.
- SQLite foreign keys are enabled on connect.
- `init_db()` creates all SQLModel tables.

Agent LLM behavior:

- `src/cognieda/agents/llm.py` reads `COGNIEDA_MODEL_NAME`, `COGNIEDA_OPENAI_BASE_URL`, and `COGNIEDA_OPENAI_API_KEY`.
- `COGNIEDA_MODEL_NAME` and `COGNIEDA_OPENAI_API_KEY` are required by `create_agent()`.
- These agent variables are not currently listed in `.env.example`.

## Normal application launch

Use the current working directory as the workspace:

```powershell
cognieda
```

Or select a workspace explicitly:

```powershell
cognieda PATH
```

The installed console script delegates to `cognieda.cli.app:main`.
`python -m cognieda` delegates to the same implementation inside an
environment containing the package. `--help` parses without application
bootstrap or model configuration.

This command is **Partially implemented** as a development Planner REPL
boundary. The supported end-to-end product CLI remains **Unsupported** because
Planner-to-Data Explorer-to-Evidence-to-SessionFrame composition is deferred.

The selected workspace owns `.cognieda/project.toml` and workspace-local
state. Root `config/*.toml` files remain optional development configuration;
installed startup does not require the source repository as the working
directory.

## Verification commands

Verification commands:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src/cognieda
```

No docs build or docs link-check command was found in the current repo.

## Tool And MCP Config

`config/agents.toml` contains worker references, while `config/mcp.toml`
contains commented examples rather than enabled servers. These configuration
entries do not establish a supported integration. See
[Current state](../status/current-state.md).

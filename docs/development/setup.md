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
COGNIEDA_MODEL_PROVIDER=google
COGNIEDA_MODEL_NAME=gemini-3.5-flash
MODEL_API_KEY=replace-with-your-provider-api-key
# MODEL_BASE_URL=https://your-provider.example/v1
COGNIEDA_DB_URL=
COGNIEDA_DB_ECHO=false
```

Database behavior:

- If `COGNIEDA_DB_URL` is empty, the provisional persistence helper resolves a
  package-local SQLite path. Runtime bootstrap does not bind this helper to the
  selected Workspace.
- SQLite foreign keys are enabled on connect.
- `init_db()` creates all SQLModel tables.

Agent LLM behavior:

- The CLI loads the selected Workspace's `.env` file without overwriting
  variables already set in the process. Copy `.env.example` to the Workspace
  root, set `MODEL_API_KEY`, and run `cognieda` from that Workspace (or pass
  its path explicitly).
- `.cognieda/project.toml` may provide `model.provider`, `model.name`,
  `model.base_url`, and `model.api_key` for the selected workspace. Non-empty
  workspace values take precedence over `.env` and process values.
- New Workspaces set the canonical `google` provider. To use `openai` or
  `anthropic`, set `model.provider` in the selected Workspace's
  `.cognieda/project.toml`; `gemini` remains an input compatibility alias for
  `google`.
- Missing workspace values fall back individually to `COGNIEDA_MODEL_PROVIDER`,
  `COGNIEDA_MODEL_NAME`, `MODEL_BASE_URL`, and `MODEL_API_KEY`. The legacy
  `COGNIEDA_OPENAI_BASE_URL` and `COGNIEDA_OPENAI_API_KEY` names remain fallback
  compatibility inputs only.
- Model name and API key are required at bootstrap. Base URL is optional and a
  user-provided value is not overwritten by a fixed router endpoint.
- Bootstrap passes the resolved configuration into the infrastructure LLM
  factory; agents do not initialize global tooling or read configuration paths
  implicitly.

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

The resolved selected path is the user research Workspace root. Initialization
creates `.cognieda/project.toml` for CogniEDA-private configuration and `data/`
as the conventional user-managed dataset directory. Optional `data/raw/` and
`data/derived/` directories, plus private `.cognieda/state/` and
`.cognieda/sessions/`, are created lazily by their eventual owners.

Datasets may also remain at explicit external paths; being inside `data/` does
not admit a DataProfile, and opening a Workspace does not ingest or copy data.
Optional agent, MCP, and skill configuration is read only from Workspace-local
`.cognieda/agents.toml`, `.cognieda/mcp.toml`, and `.cognieda/skills.toml` when
those files exist. Root `config/*.toml` files are development examples;
installed startup does not require the source repository as the working
directory. See [Workspace ownership](workspace-layout.md).

## Verification commands

Verification commands:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src/cognieda
```

No docs build or docs link-check command was found in the current repo.

## Agent and MCP configuration

`config/agents.toml` contains worker references, while `config/mcp.toml`
contains commented examples rather than enabled servers. These configuration
entries do not establish a supported integration. See
[Current state](../status/current-state.md).

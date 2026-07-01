# Development Setup

## Prerequisites

- Python 3.12+
- `uv`

## Install

From the repository root:

```powershell
uv sync
copy .env.example .env
```

## Environment

Current `.env.example` contains:

```text
COGNIEDA_ENV=local
COGNIEDA_LOG_LEVEL=INFO
COGNIEDA_DB_URL=
COGNIEDA_DB_ECHO=false
```

Database behavior:

- If `COGNIEDA_DB_URL` is empty, the default SQLite URL points to `.local/cognieda_artifacts.sqlite3`.
- SQLite foreign keys are enabled on connect.
- `init_db()` creates all SQLModel tables.

Agent LLM behavior:

- `src/agents/llm.py` reads `COGNIEDA_MODEL_NAME`, `COGNIEDA_OPENAI_BASE_URL`, and `COGNIEDA_OPENAI_API_KEY`.
- `COGNIEDA_MODEL_NAME` and `COGNIEDA_OPENAI_API_KEY` are required by `create_agent()`.
- These agent variables are not currently listed in `.env.example`.

## Commands

Current package script:

```powershell
uv run cognieda
```

Current result: the script runs `main.py`, which prints a placeholder message.

Verification commands:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

No docs build or docs link-check command was found in the current repo.

## Tool And MCP Config

`config/agents.toml` and `config/mcp.toml` exist but are empty in the audited repo. `src/tools/manager.py` can load worker MCP config when populated. Built-in tool lists are placeholders.

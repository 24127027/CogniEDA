# Development setup

This is a repository-development setup, not a product quickstart. CogniEDA has
no supported CLI, HTTP API, worker, daemon, or bootstrap package. Start at the
[contributor hub](index.md) and read the
[runtime composition](../operations/runtime-composition.md)
before wiring an adapter.

## Prerequisites

- Python 3.12+
- `uv`

## Install

From the repository root:

```powershell
uv sync
copy .env.example .env
```

## Environment and SQLite development boundary

Current `.env.example` contains:

```text
COGNIEDA_ENV=local
COGNIEDA_LOG_LEVEL=INFO
COGNIEDA_DB_URL=
COGNIEDA_DB_ECHO=false
```

Database behavior:

- Repository session helpers fall back to `.local/cognieda_graph.sqlite3` when
  `COGNIEDA_DB_URL` is empty.
- `CogniEDARuntime` itself requires a non-empty explicit database URL in
  `RuntimeConfiguration`; it does not silently select that fallback.
- SQLite foreign keys are enabled on connect.
- `init_db()` applies ordered targeted upgrades, creates missing current
  SQLModel tables, installs selected guards, and runs legacy quarantine.

See [SQLite initialization and migrations](../operations/sqlite-and-migrations.md)
for the supported fresh and existing-database boundary.

The tested persistence and concurrency boundary is SQLite. Do not infer
PostgreSQL, cross-database, or multi-host support from the SQLModel interfaces.

## In-process runtime composition

`CogniEDARuntime` is a library composition root. Its constructor requires an
authenticated-principal resolver, an explicit Hypothesis Analyst model, a Data
Explorer identifier/factory, and an execution-context factory. The
`runtime_loader` helper accepts an explicit environment-named `module:factory`;
it never invents missing adapters. These are integration seams, not a supported
product process.

Agent LLM behavior:

- `src/agents/llm.py` reads `COGNIEDA_MODEL_NAME`, `COGNIEDA_OPENAI_BASE_URL`, and `COGNIEDA_OPENAI_API_KEY`.
- `COGNIEDA_MODEL_NAME` and `COGNIEDA_OPENAI_API_KEY` are required by `create_agent()`.
- These agent variables are not currently listed in `.env.example`.

## Verification commands

```powershell
uv run pytest -q tests/architecture
uv run ruff check .
uv run pytest -q
```

Markdown structure, canonical index coverage, relative links, and local heading
anchors are checked by
`tests/architecture/test_documentation_integrity.py`.

## Unresolved tools, skills, and MCP configuration

`config/agents.toml` and `config/skills.toml` contain worker/skill
configuration. `config/mcp.toml` contains only commented examples, so the MCP
names referenced by the checked-in agent configuration are currently
undefined. The configured skill directories also contain no tracked
`SKILL.md` files. `src/tools/manager.py` loads all three surfaces and fails
explicitly on an undefined MCP reference. Supply coherent deployment
configuration before using model-backed configured Planner adapters. The
exported graph/dataset built-ins remain placeholders.

## Current verification note

Verification counts are checkout-specific and must not be copied into a release
claim. `uv run mypy src` is useful for diagnosis but has known baseline debt;
do not call it a clean gate without a current result. Select focused commands
from the [testing strategy](testing.md) before running the full suite.

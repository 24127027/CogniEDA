# CogniEDA

CogniEDA is validity-preserving research-state infrastructure for analytical
investigation. It keeps research intent, data state, planning assumptions,
scientific commitments, observations, claims, validity, provenance, and active
context distinct and traceable.

The repository currently provides partial library and SQLite persistence
foundations. It does not provide a supported end-to-end application, service,
or product CLI. See [Current state](docs/status/current-state.md) for the
evidence-qualified capability boundary.

## Development setup

Prerequisites are Python 3.12+ and `uv`.

```powershell
uv sync
copy .env.example .env
```

The default database URL resolves to `.local/cognieda_graph.sqlite3` unless
`COGNIEDA_DB_URL` is set. Current database behavior is verified on SQLite.

To run the development-only Planner REPL scaffold:

```powershell
uv run main.py
```

Repository verification commands are:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src
```

These commands are declared by the repository; passing status is not implied
by their presence.

## Documentation

Start with the [canonical documentation index](docs/index.md). It links the
conceptual foundation, architecture, scientific lifecycle, validity, context,
reference, design decisions, and current-status tracks.

The [MVP runtime subset](docs/architecture/mvp-runtime-subset.md) defines the
approved executable vertical slice and distinguishes it from the complete
canonical architecture. The end-to-end MVP remains a design target.

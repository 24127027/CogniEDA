# CogniEDA

CogniEDA is validity-preserving research-state infrastructure for analytical
investigation. It keeps research intent, data state, planning assumptions,
scientific commitments, observations, claims, validity, provenance, and active
context distinct and traceable.

The repository currently provides partial library and SQLite persistence
foundations plus an installable development Planner REPL. It does not provide
a supported end-to-end application, service, or product CLI. See
[Current state](docs/status/current-state.md) for the evidence-qualified
capability boundary.

## Development setup

Prerequisites are Python 3.12+ and `uv`.

```powershell
uv sync
uv tool install --editable .
copy .env.example .env
```

If uv's tool directory is not already on `PATH`, run `uv tool update-shell`
once and open a new shell. The editable tool installation makes later Python
source edits visible without reinstalling; refresh the tool environment after
dependency metadata changes.

The default database URL resolves to `.local/cognieda_graph.sqlite3` unless
`COGNIEDA_DB_URL` is set. Current database behavior is verified on SQLite.

Normal development launch does not require activating `.venv`:

```powershell
cognieda
cognieda PATH
```

`python -m cognieda` is also available inside an environment containing the
package. These entrypoints expose the development Planner REPL scaffold, not a
supported end-to-end product workflow.

Repository verification commands are:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src/cognieda
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

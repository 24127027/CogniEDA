# Testing

The repository declares:

```powershell
uv run pytest
uv run ruff check .
uv run mypy src/cognieda
```

`pyproject.toml` configures pytest for `tests/` and README doctests. Command
declaration does not imply that the current full suite passes.

Capability claims must be tied to the exact tests run and their result. The
[current-state page](../status/current-state.md) and
[limitations page](../status/limitations-and-bottlenecks.md) record the current
verification boundary and known failures.

When runtime invariants change, prefer focused tests for identity, admission,
immutability, cardinality, context eligibility, authority separation,
transactions, fencing, replay, and validity consequences before broader
behavior tests.

# CogniEDA

CogniEDA is validity-preserving research-state infrastructure for analytical
investigation. It keeps conclusions bound to the dataset state, analytical
contract, observed Evidence, scope, uncertainty, and validity conditions that
support them. Long-running continuity follows from that governed state; retaining
more conversation is not the primary goal.

CogniEDA is a governed research-state system, not a generic EDA chatbot, notebook
history summarizer, vector-store wrapper, autonomous scientist, or general
multi-agent framework.

## Current maturity

- **Implemented:** typed research-state objects and guarded in-process paths for
  planning approvals, execution provenance, Evidence admission, protected
  evaluation, governance, Discovery admission, validity propagation, bounded
  retrieval, and SessionFrame snapshots.
- **Verified on SQLite:** the transaction, replay, fencing, and concurrency
  behavior exercised by the current test suite.
- **Partially implemented:** the Planner, dataset acceptance workflow,
  SessionFrame governance experience, and end-to-end session-resume workflow.
- **Unsupported:** a production CLI, HTTP API, worker or daemon, production
  authentication, a concrete Data Explorer, and a default production Analyst
  model adapter.
- **Known deviation:** checked-in model-backed agent configuration references
  undefined MCP servers and skill directories without tracked definitions.
- **Deferred:** executable DVC integration, governed cleaning, Graph Miner,
  persistent semantic indexing, and Evidence Cache.

The repository currently provides an in-process Python foundation. Source code is
the authority for implemented behavior; the documentation distinguishes current
implementation from design targets and deferred work.

## Documentation

Start with the [canonical documentation journey](docs/index.md). For the
verified maturity boundary, see [current state](docs/current-state.md), the
[capability and maturity map](docs/capability-and-maturity-map.md), and the
[dependency-driven roadmap](docs/roadmap.md).

## Contributor entry points

Prerequisites are Python 3.12+ and `uv`.

```powershell
uv sync
```

See [development setup](docs/development/setup.md),
[testing](docs/development/testing.md), and
[contributing](docs/development/contributing.md) for the current repository
commands and guardrails. Start source-oriented work at the
[contributor documentation hub](docs/development/index.md).

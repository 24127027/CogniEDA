---
name: cognieda-doc-writer
description: Maintain CogniEDA documentation while preserving canonical target versus verified current implementation truth.
---

# CogniEDA documentation writer

## Required workflow

1. Inspect relevant source, tests, migrations, configuration, and repository
   state before making current claims.
2. Inspect canonical owner pages and legacy pages for the same topic.
3. Use only: `Implemented`, `Verified on SQLite`, `Partially implemented`,
   `Design target`, `Deferred`, `Known limitation`, and `Unsupported`.
4. Name the supported boundary. A file, schema, interface, stub, fixture,
   configuration key, or directory is insufficient evidence.
5. Update `docs/status/current-state.md` and relevant limitations when verified
   drift is found. The old implementation-gap path is a compatibility notice.
6. Run documentation checks and targeted capability tests when needed.

## Source priority

For current behavior, source and tests are authoritative. For target design:

1. `docs/design-decisions/index.md`
2. canonical owner pages linked as Available from `docs/index.md`
3. Planner source only as current scaffold evidence, never target authority

When target and source differ, document the difference without changing either
meaning.

## Canonical guardrails

- FCOs are exactly Objective, DataProfile, Assumption, Task, Hypothesis,
  Evidence, Discovery, and SessionFrame.
- The semantic graph contains exactly Objective, Hypothesis, Evidence, and
  Discovery.
- Task kinds are exactly `DATA`, `SCIENTIFIC`, `GRAPH`, and `SYNTHESIS`; legacy
  kinds are drift, not target compatibility.
- Planner is the sole human facade and has no scientific operationalization or
  evaluation authority.
- Data Explorer exclusively accesses datasets and does not evaluate.
- Hypothesis Analyst owns scientific work but has no dataset access.
- Graph Miner is read-only.
- Governance does not rewrite; application authority alone admits durable
  state.
- Assumptions are planning-only and excluded from protected evaluation.
- Cross-Objective use, ambiguous lineage, and legacy fallback fail closed.

## Documentation guardrails

- Keep concept, architecture, lifecycle, validity, context, reference,
  decision, and status ownership distinct.
- Convert superseded paths to concise compatibility notices when inbound links
  still matter.
- Do not expose review packs, prompt history, branch chronology, or owner-review
  mechanics in public docs.
- Do not invent commands, APIs, services, dependencies, database support,
  integrations, or runtime composition.
- Keep README concise and route through `docs/index.md`.

## Completion report

Report changed files, implementation boundaries and gaps, design/code drift,
legacy dispositions, exact checks, unresolved risks, and special-review pages.

# System Architecture Overview

> **Status**: `[Implemented]` / `[Verified on SQLite]`

CogniEDA is structured around a multi-tier, governed architecture designed to guarantee conclusion validity, context type safety, and multi-session continuity.

---

## 1. High-Level Architectural Tiers

```text
┌───────────────────────────────────────────────────────────┐
│                      User Interface / CLI                 │
│         (Target Package 7 Product Slice - Unsupported)     │
└─────────────────────────────┬─────────────────────────────┘
                              │
┌─────────────────────────────▼─────────────────────────────┐
│                    Application Layer                      │
│   (execution, evidence, evaluation, governance,           │
│    discovery, validity, orchestrator, events)             │
└──────┬──────────────────────┬──────────────────────┬──────┘
       │                      │                      │
┌──────▼──────┐        ┌──────▼──────┐        ┌──────▼──────┐
│  Specialist │        │    Schemas  │        │Repositories │
│    Agents   │        │   Bounded   │        │   Bounded   │
│ (Explorer / │        │   Context   │        │   Context   │
│  Analyst)   │        │   Models    │        │   Adapters  │
└─────────────┘        └──────┬──────┘        └──────┬──────┘
                              │                      │
                       ┌──────▼──────────────────────▼──────┐
                       │          Database Models           │
                       │     (db.models canonical facade)   │
                       └──────────────────┬─────────────────┘
                                          │
                       ┌──────────────────▼─────────────────┐
                       │         SQLite Database Engine     │
                       │ (immediate locking & DDL triggers) │
                       └────────────────────────────────────┘
```

---

## 2. Core Architectural Invariants

1. **Strict Context Isolation**: Specialized agent roles operate only within their assigned contexts. Data Explorer performs code execution and technical observations. Hypothesis Analyst evaluates evidence and proposes claims.
2. **Single Transaction Owners**: Atomic operations (Discovery materialization, validity propagation, execution transitions) have exactly one owning application service. Direct database mutations by unauthorized components are strictly forbidden.
3. **Immutable Epistemic Records**: `DataProfile`, `Evidence`, `Discovery`, `ValidityEvent`, `GovernanceAuthority`, and `ProposalDecision` objects are immutable once written.
4. **Governed Materialization**: A `Discovery` cannot be created directly by an LLM agent or planner node. It requires a protected synthesis bundle, formal proposal, user decision, and fenced atomic admission.

---

## 3. Key Subsystems

- **Research State Management**: [research-state-model.md](research-state-model.md)
- **Scientific Specialist Boundaries**: [scientific-specialist-contracts.md](scientific-specialist-contracts.md)
- **Bounded Contexts**: [bounded-contexts.md](bounded-contexts.md)
- **Persistence & Transactions**: [persistence-and-transactions.md](persistence-and-transactions.md)
- **Validity & Invalidation Engine**: [validity-and-invalidation.md](validity-and-invalidation.md)

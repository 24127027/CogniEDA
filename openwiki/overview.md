---
type: System Overview
title: CogniEDA Architecture Overview
description: High-level view of CogniEDA's validity-preserving research-state infrastructure, core concepts, authority model, and major components.
tags: [architecture, design, system, research-state]
---

# CogniEDA Architecture Overview

## What is CogniEDA?

**CogniEDA** is validity-preserving research-state infrastructure for analytical investigation. It solves a fundamental problem: conversations don't reliably distinguish between planning ideas, assumptions, observations, evaluated claims, and stale findings.

CogniEDA treats research state as **governed state**, not remembered prose. It keeps investigation explicit, traceable, restrained, and safe to resume across sessions.

### Architectural Priorities

In order:
1. **Conclusion validity and traceability** - Every claim is grounded in evidence with clear authority
2. **Context type safety** - Different reasoning modes work with appropriate data types
3. **Multi-session continuity** - State resumes reliably; nothing is lost or accidentally reused
4. **Speed and convenience** - Powerful workflows don't require boilerplate

## Core Concept: Research State Separation

Research state contains eight First-Class Objects (FCOs):

### Semantic Knowledge Graph (4 FCOs)

- **Objective** - Research intent and planned work
- **Hypothesis** - Testable claim to evaluate
- **Evidence** - Immutable observed analytical result
- **Discovery** - Final admitted scientific claim

### Additional FCOs (4)

- **DataProfile** - Immutable snapshot of a dataset
- **Assumption** - Planning-only statement (not scientific fact)
- **Task** - Semantic unit of work in the DAG
- **SessionFrame** - Active reasoning context and membership

Each FCO has distinct lifecycle rules, authority boundaries, and validity propagation behavior.

## Authority Model

Eight independent authorities ensure no artifact silently acquires a stronger epistemic role:

1. **Human** - Sets research intent and approves plans
2. **Planner** - Coordinates objectives and tasks
3. **Data Admission** - Validates and profiles datasets
4. **Execution** - Runs and reports analytical work
5. **Evidence** - Records observed results
6. **Scientific** - Evaluates claims against evidence
7. **Discovery** - Admits final evaluated claims
8. **Context** - Governs what is active and available

Each authority owns specific state transitions. No authority can bypass another.

## Three-Plane Architecture

CogniEDA is organized in three planes:

```
┌─────────────────────────────────────────────┐
│ Authority Plane                             │
│ (Human decisions, validity judgments)       │
├─────────────────────────────────────────────┤
│ Control Plane                               │
│ (Planning, coordination, dispatch)          │
├─────────────────────────────────────────────┤
│ Specialist Plane                            │
│ (Data exploration, analysis, execution)     │
└─────────────────────────────────────────────┘
```

### Specialist Plane

Four specialist agents handle domain work:

- **Data Explorer** - Profile datasets, identify properties
- **Graph Miner** - Extract relationships and patterns
- **Hypothesis Analyst** - Evaluate claims against evidence
- **Planner** - Coordinate objectives and task DAGs

### Control Plane

- **Execution Dispatcher** - Route work to specialists
- **Admission Services** - Validate state transitions
- **Transition Service** - Orchestrate multi-step flows
- **Persistence Layer** - SQLite-backed state repository

### Authority Plane

- **Human interface** - Plan approval, objective setting
- **Scientific judgment** - Evidence evaluation
- **Discovery approval** - Claim admission
- **Context curation** - Active data selection

## Persistence Model

CogniEDA uses **SQLite by default** with optional external database support.

- **Workspace-local**: `.cognieda/.cognieda.db` in each research workspace
- **Configuration**: Set `COGNIEDA_DB_URL` for external databases
- **Immutability**: FCOs are write-once; changes create new versions
- **Audit trail**: All state changes recorded with provenance

## Configuration

Configuration is workspace-first:

```toml
# .cognieda/project.toml
model.provider = "google"  # or "openai", "anthropic"
llm.temperature = 0.7
execution.timeout = 300
```

Environment variables override workspace config:

```powershell
$env:MODEL_API_KEY = "sk-..."
$env:COGNIEDA_MODEL_PROVIDER = "openai"
```

## Key Workflows

### 1. Research Setup
1. Create workspace with objectives
2. Load and profile dataset (DataProfile created)
3. Define assumptions (Assumption records)

### 2. Hypothesis Generation
1. Planner creates Tasks based on objective
2. Hypothesis Analyst generates Claims
3. Human reviews and approves hypotheses

### 3. Analysis Execution
1. Data Explorer runs profiling, validation
2. Graph Miner extracts patterns
3. Results recorded as Evidence

### 4. Evidence Evaluation
1. Hypothesis Analyst compares claims to evidence
2. Scientific authority judges fit
3. Approved claims become Discoveries

### 5. Session Resume
1. Load SessionFrame with prior context
2. Retrieve eligible Evidence and Discoveries
3. Continue analysis from known state

## Extension Points

CogniEDA provides seven extension mechanisms:

1. **Custom Agents** - Implement specialist protocol
2. **Tool Registry** - Add execution capabilities
3. **LLM Factory** - Support new model providers
4. **Database Adapter** - Use alternative storage
5. **Configuration Schema** - Extend project.toml
6. **Validation Rules** - Custom data contracts
7. **Skills Loader** - Add external tools via MCP

## Current Status

**MVP Runtime** (Foundation Complete):
- ✓ Research state model (8 FCOs)
- ✓ Authority boundaries (8 authorities)
- ✓ Persistence layer (SQLite)
- ✓ CLI and REPL
- ✓ Specialist agents
- ✓ Planning and execution

**Deferred** (Not in MVP):
- Orchestration layer (multi-step workflows)
- End-to-end application
- Production service deployment
- Horizontal scaling

See [Current State](./status/current-state.md) for detailed capability boundaries.

## Next Steps

- **Getting Started**: [Quick Start](./quickstart.md)
- **Deep Dive**: [Architecture Deep Dive](./architecture/deep-dive.md)
- **API Reference**: [Component Reference](./reference/components.md)
- **Development**: [Development Guide](./development/setup.md)

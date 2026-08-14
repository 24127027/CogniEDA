---
type: Concept Reference
title: CogniEDA Research State Concepts
description: Explanation of research state separation, First-Class Objects (FCOs), authority model, and how CogniEDA keeps investigation explicit and traceable.
tags: [concepts, research-state, authority, design]
---

# Research State Concepts

## The Problem CogniEDA Solves

In typical analytical conversations, statements blur together:

- "I think we should check the outliers" (planning idea)
- "Customers typically spend $100" (assumption)
- "The median is $87" (observed result)
- "Therefore, premium customers spend 2x the average" (evaluated claim)
- "We confirmed in our study that..." (stale finding from last week)

All are represented as text. A model can't reliably tell which is which.

**Consequence**: Investigation becomes unreliable. Assumptions harden into facts. Stale findings get reused. Previous context gets lost. Sessions cannot safely resume.

## CogniEDA's Solution: Governed Research State

CogniEDA treats research state as **governed state**, not remembered prose.

Instead of mixing types in conversation:

```
Human:        "Let me analyze this data"
Model:        "I'll profile the dataset"
Model:        "Here's what I found..."
Human:        "Great, so we can assume..."
(Later)
Human:        "Did we prove that yet?"
(Nobody knows what's proven vs. assumed vs. just talked about)
```

CogniEDA separates them:

```
Research State                      Type              Authority
─────────────────────────────────────────────────────────────
User says: "Analyze churn"     → Objective         Human
Planner breaks into tasks      → Tasks             Planner
Analysis runs, returns number  → Evidence          Execution
"Does this prove hypothesis?" → Evaluation        Scientific
"Yes, I accept this"          → Discovery         Authority
"I'll remember this next time"→ SessionFrame       Context
```

Each object has:
- **Distinct lifecycle** (when it's created, how it changes)
- **Clear authority** (who controls it)
- **Type safety** (what operations are legal)
- **Traceability** (where it came from)

## Eight First-Class Objects (FCOs)

CogniEDA governs eight types of research state:

### Semantic Knowledge Graph (4 FCOs)

These form the core scientific reasoning chain.

#### 1. Objective

**What it is**: Research intent captured in language-independent form

**Who creates it**: Human authority

**Lifecycle**:
- Created when user states research direction
- Active during investigation
- Completed when findings are finalized
- Can be revised, but new version != old version

**Constraints**:
- Must be explicit and bounded
- "Analyze all data" is not valid (too broad)
- "Understand why churned customers differ" is valid (specific scope)

**Example**:
```
Objective {
  id: "obj-001"
  intent: "Identify which factors most influence customer retention"
  scope: "2024 customer data, 100K+ users"
  created_by: "human"
  created_at: 2026-08-14T10:00:00Z
}
```

**Queries**:
- What objectives are currently active?
- Which discoveries support this objective?
- How did this objective evolve over time?

#### 2. Hypothesis

**What it is**: A testable claim derived from an objective

**Who creates it**: Hypothesis Analyst (specialist agent)

**Lifecycle**:
- Generated from objective context
- Proposed to user
- Under evaluation (compared against evidence)
- Confirmed (becomes eligible for use) or rejected

**Constraints**:
- Must be specific and measurable
- Must relate to parent objective
- Cannot become a discovery without evidence

**Example**:
```
Hypothesis {
  id: "hyp-042"
  objective_id: "obj-001"
  claim: "Monthly subscription churn correlates negatively with email engagement"
  generated_at: 2026-08-14T10:05:00Z
  confidence: 0.65
}
```

**Queries**:
- What hypotheses are under evaluation?
- Which evidence supports this claim?
- Why was this hypothesis rejected?

#### 3. Evidence

**What it is**: Immutable observed analytical result with full provenance

**Who creates it**: Any specialist agent during execution

**Lifecycle**:
- Generated during analysis
- Recorded with full provenance (task, agent, input, parameters)
- Subject to validity assessment (is source data still valid?)
- Can remain valid or be invalidated

**Constraints**:
- Write-once (cannot be changed after recording)
- Must include provenance (how it was derived)
- Must be reproducible (someone else can run same analysis)

**Example**:
```
Evidence {
  id: "evd-156"
  analysis_id: "task-033"
  result: {
    correlation: 0.72,
    p_value: 0.0001,
    sample_size: 45000
  }
  provenance: {
    agent: "graph_miner",
    input_data: "profile-2026-08-14",
    method: "pearson_correlation",
    parameters: {temperature: 0.0}
  }
  recorded_at: 2026-08-14T10:15:00Z
}
```

**Queries**:
- What evidence supports this discovery?
- Is this evidence still valid?
- Who generated this result?

#### 4. Discovery

**What it is**: Final evaluated claim eligible for use in future analysis

**Who creates it**: Scientific authority + Discovery authority

**Lifecycle**:
- Proposed when evidence strongly supports a hypothesis
- Under review (human judgment)
- Admitted (authority accepts it as fact for this project)
- Can be retracted if assumptions change

**Constraints**:
- Cannot be created without supporting evidence
- Requires human approval
- Retracting a discovery invalidates dependent work

**Example**:
```
Discovery {
  id: "disc-089"
  hypothesis_id: "hyp-042"
  claim: "Monthly subscription churn correlates negatively with email engagement"
  evidence_ids: ["evd-156", "evd-158", "evd-161"]
  admitted_at: 2026-08-14T10:45:00Z
  admitted_by: "human"
}
```

**Queries**:
- What discoveries are available for reuse?
- Which discoveries are still valid?
- What was the reasoning for this discovery?

### Supporting Objects (4 FCOs)

These enable correct planning and context management.

#### 5. DataProfile

**What it is**: Immutable snapshot of dataset metadata at capture time

**Who creates it**: Data Explorer

**Lifecycle**:
- Created when data is first loaded
- Immutable (represents "this data at this moment")
- Can be superseded (new version when data changes)
- Used to validate evidence reproducibility

**Constraints**:
- Captures structure, not content (no row-level storage)
- Includes schema, row count, missing values, types
- Cannot be edited; new data means new profile

**Example**:
```
DataProfile {
  id: "prof-284"
  source: "data/customers_2024.csv"
  columns: [
    {name: "customer_id", type: "string", non_null_count: 100000},
    {name: "lifetime_value", type: "float", non_null_count: 98500},
    ...
  ]
  row_count: 100000
  created_at: 2026-08-14T09:30:00Z
}
```

**Queries**:
- What data was available when this analysis ran?
- Has the source data changed since this evidence?
- What columns were in scope for this discovery?

#### 6. Assumption

**What it is**: Temporary working assumption during planning (not scientific fact)

**Who creates it**: Human or Planner

**Lifecycle**:
- Created during planning phase
- Used to guide task generation
- Revisited (questioned and validated or discarded)
- Cannot become permanent without evidence

**Constraints**:
- Explicitly temporary (not in scientific chain)
- Must be clearly stated
- Separate from evidence and discoveries

**Example**:
```
Assumption {
  id: "assum-021"
  statement: "Customer lifetime value is normally distributed"
  objective_id: "obj-001"
  scope: "planning only - needs verification"
  created_at: 2026-08-14T10:00:00Z
}
```

**Queries**:
- What assumptions guide this plan?
- Which assumptions were validated?
- Which led to incorrect conclusions?

#### 7. Task

**What it is**: Semantic unit of work in the execution DAG

**Who creates it**: Planner

**Lifecycle**:
- Generated from objective decomposition
- Assigned to specialist agent
- Executed and produces Evidence
- Completed or failed

**Constraints**:
- Must be specific and bounded
- Must have clear dependencies
- Cannot execute without parent objective

**Example**:
```
Task {
  id: "task-033"
  objective_id: "obj-001"
  description: "Calculate correlation between email engagement and churn"
  dependencies: ["task-031", "task-032"]
  assigned_to: "graph_miner"
  created_at: 2026-08-14T10:05:00Z
}
```

**Queries**:
- What tasks are pending?
- Which tasks produced this evidence?
- What's the dependency graph?

#### 8. SessionFrame

**What it is**: Bookmark of active context for safe multi-session resume

**Who creates it**: Context authority (human)

**Lifecycle**:
- Created before context switch
- Captures current objective, active evidence, discoveries
- Used to restore context in future session
- Enables safe resume without information loss

**Constraints**:
- Snapshot at creation time (immutable)
- Must explicitly include what to remember
- Next session can filter what to use

**Example**:
```
SessionFrame {
  id: "frame-007"
  created_at: 2026-08-14T11:00:00Z
  active_objective_id: "obj-001"
  eligible_evidence_ids: ["evd-156", "evd-158"],
  eligible_discovery_ids: ["disc-089"],
  context_notes: "Correlation analysis complete; ready for causality exploration"
}
```

**Queries**:
- What context was active at point X?
- Can we safely resume from this frame?
- What data was eligible in that session?

## Authority Model: Eight Independent Powers

Each type of state transition is owned by exactly one authority. This prevents any artifact from silently acquiring a stronger epistemic role.

### The Eight Authorities

| Authority | Owns | Cannot Do |
|-----------|------|-----------|
| **Human** | Objectives, plan approval | Cannot approve discoveries without scientific eval |
| **Planner** | Task generation, DAG | Cannot execute tasks; cannot change objective |
| **Data Admission** | Dataset eligibility | Cannot modify data; cannot create evidence |
| **Execution** | Job success/failure | Cannot validate data; cannot approve results |
| **Evidence** | Recording results | Cannot evaluate results; cannot approve claims |
| **Scientific** | Claim-evidence fit | Cannot execute analysis; cannot admit final discovery |
| **Discovery** | Final claim admission | Cannot generate evidence; cannot retract without approval |
| **Context** | Active session data | Cannot change what's in scope for analysis |

### How They Interact

```
Human says: "Analyze churn"
    ↓ (Human authority decides intent)
Planner creates Tasks
    ↓ (Planner authority decomposes work)
Execution runs tasks
    ↓ (Execution authority confirms completion)
Evidence recorded
    ↓ (Evidence authority accepts result)
Scientific evaluates
    ↓ (Scientific authority judges fit)
Discovery admitted
    ↓ (Discovery authority accepts claim)
Context stored
    ↓ (Context authority remembers it)
(Next session)
Human retrieves SessionFrame
    ↓ (Context authority restores scope)
Analysis resumes safely
```

Each step requires the next authority. No authority can skip others.

## Validity States and Propagation

Not all state is equally trustworthy. Validity has four states:

```python
PROVISIONAL      # Temporary assumption; needs verification
    ↓
ASSERTED         # Claimed but not yet checked
    ↓
EVIDENCE_BASED   # Grounded in current evidence
    ↓
RETRACTED        # Explicitly invalidated
```

### Validity Propagation Rules

**Discovery depends on Evidence**:
- If Evidence becomes RETRACTED → Discovery becomes PROVISIONAL (needs new evidence)
- If source DataProfile superseded → Evidence becomes ASSERTED (source changed)

**Hypothesis depends on Objective**:
- If Objective scope shrinks → Hypothesis may become invalid
- If Objective fundamentals change → Hypotheses need re-evaluation

**Assumptions need verification**:
- Can start as PROVISIONAL
- Must become EVIDENCE_BASED or be RETRACTED
- Cannot remain PROVISIONAL in final discoveries

## Type Safety and Context Modes

Different reasoning modes require different data types:

### Planning Mode
- Can use: Objectives, Assumptions, Tasks, prior Discoveries
- Cannot use: Provisional hypotheses, unvalidated evidence
- Authority: Planner validates scope and assumptions

### Execution Mode
- Can use: Current Tasks, DataProfiles, existing tools
- Cannot use: Objectives not decomposed into tasks
- Authority: Execution validates task readiness

### Scientific Mode
- Can use: Evidence, confirmed Hypotheses
- Cannot use: Planning assumptions, unvalidated data
- Authority: Scientific validates fit and provenance

### Recall Mode (Resume)
- Can use: SessionFrame + eligible Evidence/Discoveries
- Cannot use: Data outside session scope
- Authority: Context governs eligibility

Type safety prevents mixing inappropriate data types.

## Why This Matters

### For Researchers

- **Explicit**: You know what's proven vs. assumed vs. just explored
- **Safe resume**: Sessions can pause and continue without losing reasoning
- **Traceable**: Full chain from question to conclusion
- **Auditable**: Anyone can follow the logic

### For Teams

- **Shared understanding**: Team members see same state, not interpreted prose
- **No surprises**: Changes in validity propagate explicitly
- **Reversible**: Retracting discoveries doesn't lose history
- **Collaborative**: Multiple people can safely work on same project

### For Systems

- **Type-safe**: Invalid transitions prevented at design level
- **Automatable**: State machine enables delegation to agents
- **Auditable**: Complete lineage for compliance
- **Scalable**: Immutability enables safe parallelization


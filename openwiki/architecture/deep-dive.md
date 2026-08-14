---
type: Architecture Deep Dive
title: CogniEDA Architecture Deep Dive
description: Comprehensive technical design of CogniEDA including three-plane model, authority boundaries, data flows, state machines, and extensibility.
tags: [architecture, design, technical, authority]
---

# CogniEDA Architecture Deep Dive

## Architecture Principles

CogniEDA is organized around three core principles, in priority order:

### 1. Authority Separation

**No artifact should silently acquire a stronger epistemic role.**

Each state transition is owned by exactly one authority. An object cannot change roles without explicit approval from that authority. This prevents:

- Evidence being treated as proven fact without scientific evaluation
- Assumptions becoming permanent scientific commitments
- Stale findings being reused without validity check
- Planning ideas hardening into requirements without human approval

### 2. Immutability with Versioning

**Research state is append-only; changes create new versions.**

- First-Class Objects (FCOs) are write-once
- Updates create new versions with lineage tracking
- All versions remain queryable for audit and continuity
- Validity propagation follows version history

Benefits:
- Complete audit trail of all decisions
- Safe multi-session resume
- Retraction doesn't require deletion
- Historical context always available

### 3. Type-Safe Context

**Different reasoning modes work with different data types.**

- Planning mode: Can use Assumptions, provisional Tasks
- Scientific mode: Only evaluated Evidence and Discoveries
- Execution mode: Current Tasks and DataProfiles
- Resume mode: Prior SessionFrames filter eligible data

Invalid combinations are prevented at the type level.

## Three-Plane Architecture

```
┌──────────────────────────────────────────────────┐
│ Authority Plane                                  │
│ • Human decision-making                          │
│ • Scientific judgment & validity                 │
│ • Discovery approval                             │
│ • Context curation                               │
├──────────────────────────────────────────────────┤
│ Control Plane (Orchestration & Routing)          │
│ • Planner: Objective coordination                │
│ • Dispatcher: Task routing                       │
│ • Admission Services: Validation                 │
│ • Transition Service: Multi-step flows           │
├──────────────────────────────────────────────────┤
│ Specialist Plane (Domain Work)                   │
│ • Data Explorer: Profiling & validation          │
│ • Graph Miner: Pattern extraction                │
│ • Hypothesis Analyst: Claim evaluation           │
│ • Custom Agents: Domain-specific tools           │
└──────────────────────────────────────────────────┘
```

### Authority Plane

Owned by: Application and human user

**Responsibilities:**
- Objective creation and approval
- Research direction changes
- Final discovery approval
- Context curation (what to remember)
- Validity judgments

**Boundaries:**
- Cannot bypass scientific evaluation
- Cannot make untraced changes
- Cannot violate validity rules

### Control Plane

Owned by: Planning and dispatch services

**Responsibilities:**
- Parse objectives into tasks
- Route tasks to specialists
- Validate state transitions
- Coordinate multi-step workflows
- Manage admission gates

**Boundaries:**
- Cannot approve discoveries (Authority owns this)
- Cannot execute user tasks directly (Specialist owns this)
- Cannot modify persisted state without validation

### Specialist Plane

Owned by: Agent implementations

**Responsibilities:**
- Execute analytical work
- Generate proposals (hypotheses, patterns)
- Create Evidence from analysis
- Profile and validate data
- Return results for evaluation

**Boundaries:**
- Cannot approve claims (Scientific authority owns this)
- Cannot modify task DAG (Planning owns this)
- Cannot decide what enters context (Authority owns this)

## Eight-Authority Model

Each authority owns specific state transitions:

| Authority | Owns | Guards | Examples |
|-----------|------|--------|----------|
| Human | Objectives, plan approval | Intent, scope | "Analyze customer churn" |
| Planner | Tasks, task DAG | Objective decomposition | Task dependencies |
| Data Admission | DataProfiles | Dataset eligibility | "Dataset valid for analysis" |
| Execution | ExecutionRuns | Work completion | Job success/failure |
| Evidence | Evidence records | Observation recording | Raw analysis results |
| Scientific | Evaluation results | Claim-evidence fit | "Hypothesis matches data" |
| Discovery | Discoveries | Final claim admission | "Claim approved as fact" |
| Context | SessionFrames | Active data eligibility | What's in scope for next session |

**Interaction Pattern:**

```
Human → Planner → Execution → Evidence → Scientific → Discovery → Context
```

Each step requires the next authority's approval.

## First-Class Objects (FCOs) Lifecycle

### Objective

```
Created by: Human authority
State flow: Active → Completed | Rejected
Owned by: Human + Planner
Validity: Eternal unless explicitly retracted
```

**Purpose:** Capture research intent in language-independent form

**Queries:**
- "What objectives are active?"
- "Which objectives produced which discoveries?"
- "What changed between objective versions?"

### Hypothesis

```
Created by: Hypothesis Analyst (specialist)
State flow: Proposed → Under Evaluation → Confirmed | Rejected
Owned by: Human approval → Scientific evaluation
Validity: Depends on evidence validity
```

**Purpose:** Testable claim derived from objective

**Queries:**
- "What hypotheses match this objective?"
- "Which evidence evaluates this hypothesis?"
- "What is the confidence for this claim?"

### Evidence

```
Created by: Any specialist agent
State flow: Generated → Recorded → Validity assessed
Owned by: Execution → Scientific authority
Validity: Can become invalid if source data invalidated
```

**Purpose:** Immutable record of analytical result with full provenance

**Queries:**
- "What evidence supports this discovery?"
- "What analysis produced this result?"
- "Is this evidence still valid?"

### Discovery

```
Created by: Scientific authority
State flow: Proposed → Admitted | Retracted
Owned by: Scientific → Discovery authority
Validity: Approved research conclusion; can be retracted
```

**Purpose:** Final evaluated claim eligible for use in future analysis

**Queries:**
- "What discoveries are available?"
- "Which claims are active?"
- "What is the audit trail for this fact?"

### DataProfile

```
Created by: Data Explorer
State flow: Profiled → Active | Superseded
Owned by: Data Admission → Execution
Validity: Immutable snapshot; superseded by new profiles
```

**Purpose:** Immutable metadata about dataset state at capture time

**Queries:**
- "What columns are in this dataset?"
- "What is the row count as of this date?"
- "Has this data been validated?"

### Assumption

```
Created by: Human or Planner
State flow: Recorded → Revisited | Superseded
Owned by: Planning authority
Validity: Planning-only; not scientific fact
```

**Purpose:** Temporary working assumption during planning phase

**Queries:**
- "What assumptions guide this plan?"
- "Which assumptions were wrong?"
- "Can we proceed with these assumptions?"

### Task

```
Created by: Planner
State flow: Planned → Assigned → Running → Complete | Failed
Owned by: Planner → Execution
Validity: Depends on parent objective
```

**Purpose:** Semantic unit of work in execution DAG

**Queries:**
- "What tasks are pending?"
- "Which tasks produced this evidence?"
- "What is the dependency graph?"

### SessionFrame

```
Created by: Context authority
State flow: Created → Active → Closed
Owned by: Authority plane
Validity: Snapshot of active context at moment of creation
```

**Purpose:** Bookmark for safe multi-session resume

**Queries:**
- "What was the context at this point?"
- "What was eligible data for this session?"
- "Can we resume from this frame?"

## Data Flow: End-to-End Analysis

```
1. Human sets Objective
   └→ Planner creates Tasks and TaskDAG

2. User confirms plan
   └→ Dispatcher routes Tasks to specialists

3. Specialist executes (e.g., Data Explorer)
   └→ Generates Evidence with provenance

4. Execution records Evidence
   └→ Triggers Scientific evaluation

5. Hypothesis Analyst evaluates
   └→ Compares Hypothesis against Evidence
   └→ Generates Evaluation

6. Authority judges fit
   └→ Approves or rejects

7. If approved, Discovery is created
   └→ Becomes eligible for future analysis

8. Human creates SessionFrame
   └→ Bookmarks current context
```

## Validity Propagation

Validity is not binary; it has multiple states:

```python
class ValidityState(Enum):
    PROVISIONAL = "planning"      # Temporary assumption
    ASSERTED = "unverified"        # Claimed but not checked
    EVIDENCE_BASED = "verified"    # Grounded in current evidence
    RETRACTED = "invalid"          # Explicitly invalidated
```

**Propagation Rules:**

- **Discovery invalidity**: Makes dependent Hypotheses questionable
- **DataProfile supersession**: Invalidates Evidence from old profile
- **Objective change**: May invalidate related Discoveries
- **Assumption revision**: Requires re-evaluation of dependent work

## Configuration Evolution

CogniEDA uses workspace-first configuration:

**Priority order** (highest to lowest):
1. Environment variables
2. `.cognieda/project.toml` (workspace-local)
3. Built-in defaults

**Precedence example:**
```
COGNIEDA_MODEL_PROVIDER=openai
  ↑ (overrides)
model.provider="google" in project.toml
  ↑ (overrides)
Built-in default: "google"
```

**Multi-workspace support:**

Each workspace has independent:
- Model configuration
- Database (local SQLite or external URL)
- Assumptions and planning state
- Active sessions

This enables:
- Isolated research projects
- Different team collaborations
- Reproducible comparisons

## Extension Points

### 1. Custom Specialists

Implement SpecialistAgent interface:

```python
class CustomAgent(SpecialistAgent):
    @property
    def capabilities(self) -> Capabilities:
        return Capabilities(name="custom", tools=[...])
    
    async def process(self, task: Task) -> Evidence:
        # Your logic
```

### 2. Tool Registry

Add execution capabilities:

```python
registry.register_capability(
    name="my_analysis",
    handler=my_tool_function
)
```

### 3. LLM Factory

Support new model providers:

```python
class CustomLLMFactory(LLMFactory):
    def create_client(self, provider: str, api_key: str):
        if provider == "custom":
            return CustomClient(api_key)
```

### 4. Database Adapter

Use alternative persistence:

```python
class PostgresAdapter(DatabaseAdapter):
    async def connect(self):
        # Connect to PostgreSQL
```

### 5. Validation Rules

Add data contracts:

```python
pandera.Column("age", int, checks=pa.checks.greater_than(0))
```

### 6. Configuration Schema

Extend project.toml:

```toml
[custom_tool]
setting1 = "value"
setting2 = 42
```

### 7. Skills Loader

Add external tools via MCP:

```python
skills_loader.load_skill("s3://my-skills/analyzer.zip")
```

## Error Handling and Recovery

### Authority Violations

```python
try:
    await evidence_repo.save(evidence)
    # This fails if scientific authority hasn't evaluated
except InvalidStateTransition as e:
    logger.error(f"Cannot save evidence: {e}")
    # Evidence must wait for scientific evaluation
```

### Validity Degradation

```python
# If source DataProfile is superseded
evidence.validity = ValidityState.ASSERTED
# Dependent discoveries flagged for review
discovery.validity = ValidityState.PROVISIONAL
```

### Execution Failure Recovery

```python
try:
    result = await dispatcher.dispatch(task)
except ExecutionError:
    # Task remains in queue
    # Can be retried, reassigned, or removed
    # Evidence not created until success
```

## Performance and Scaling

### MVP Constraints

- **SQLite only** for MVP (not production)
- **Single-machine execution** (no distributed workers)
- **Synchronous authority checks** (no async approval)
- **In-memory caching** (no distributed cache)

### Path to Scaling

1. **External database** (PostgreSQL, etc.)
2. **Distributed execution** (worker pool)
3. **Async authority** (approval queues)
4. **Cache layer** (Redis for hot data)
5. **Sharding by workspace** (tenant isolation)

### Current Performance Targets

- Objective creation: < 100ms
- Task generation: < 1s
- Evidence recording: < 500ms
- Discovery admission: < 2s
- Session resume: < 5s

## Security Considerations

### Authority Enforcement

- No state changes without authority validation
- All transitions audited and immutable
- Cross-authority decisions require witness records

### Data Isolation

- Workspaces are isolated
- DataProfiles immutable once recorded
- Assumptions cannot escape planning scope

### Audit Trail

- Every state change timestamped
- All authority transitions recorded
- Full lineage available for discovery

## Testing Architecture

### Unit Tests

- Agent implementation
- Repository operations
- Schema validation

### Integration Tests

- Multi-agent workflows
- Authority transitions
- Persistence round-trips

### E2E Tests

- Full analysis from objective to discovery
- Multi-session resume
- Error recovery

### Mock Application

Development mode with fake LLM for rapid iteration.


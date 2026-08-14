# CogniEDA Architecture Deep Dive

Comprehensive exploration of system design, component interactions, and authority boundaries.

---

## Architecture Principles

### Priority Order
1. **Conclusion validity and traceability** - Epistemic correctness first
2. **Context type safety** - Typed boundaries between state domains
3. **Multi-session continuity** - Safe restart and resume
4. **Speed and convenience** - After the first three are protected

### Core Design Pattern: Authority Separation

No useful model output, execution result, or persistence operation can silently acquire a stronger epistemic role.

**Authority Does Not Imply**:
- Planner output → Scientific authorship
- Specialist output → Evidence admission
- Persistence → Scientific interpretation
- Model generation → Governance approval

Each transition requires explicit authority validation at a boundary.

---

## Three-Plane Architecture

### Plane 1: Control Plane (Human + Planner)

**Responsibilities**:
- Establish research intent
- Coordinate investigation strategy
- Propose plans and task DAGs
- Explain reasoning to human
- Request clarification and approval
- Manage session context

**Boundaries**:
- Never writes scientific or Evidence state
- Never acquires persistence authority
- Proposes only; authority validates
- Human approval required for significant plans

**Components**:
- Human (via REPL)
- Planner agent (reasoning)
- Workspace (configuration)
- Application (orchestration)
- ConversationHistory (context)

### Plane 2: Specialist Plane (Bounded Providers)

**Responsibilities**:
- Execute role-specific work
- Return typed, bounded results
- Provide observations (not Evidence)
- Support planning consultations

**Boundaries**:
- Never acquire persistence authority
- Never write semantic graph
- Never communicate directly with human
- Restart-safe (stateless or replay-safe)

**Components**:
- Data Explorer (analysis)
- Hypothesis Analyst (science - deferred)
- Graph Miner (inquiry - deferred)
- ExecutorRegistry (dispatch)
- ExecutorDispatcher (routing)

### Plane 3: Authority Plane (Governance + Persistence)

**Responsibilities**:
- Validate exact contracts at boundaries
- Authorize state transitions
- Manage durable persistence
- Apply lifecycle transitions
- Enforce validity constraints
- Make final governance decisions

**Boundaries**:
- Cannot rewrite scientific content
- Cannot bypass specialist boundaries
- Cannot grant unvalidated authority
- Must preserve audit trail

**Components**:
- Application Authority
- Governance (deferred)
- Admission boundary (commit_planner_operations)
- Persistence layer (SQLModel)
- Validity transition service (deferred)

---

## Data Flow Architecture

### User Interaction Boundary

```
┌─────────────────────────────────────┐
│  Human                              │
│  (Research intent, approvals)       │
└──────────────┬──────────────────────┘
               │
        (ONLY boundary)
               │
┌──────────────▼──────────────────────┐
│  Planner                            │
│  (Reasoning, planning)              │
│  ├─ Frame needs                     │
│  ├─ Request consultation            │
│  └─ Propose plans                   │
└──────────────┬──────────────────────┘
               │
        (Normalized results)
               │
┌──────────────▼──────────────────────┐
│  Application Coordination            │
│  ├─ Dispatch execution              │
│  ├─ Normalize results               │
│  └─ Manage state transitions        │
└──────────────┬──────────────────────┘
               │
    (Capability-based dispatch)
               │
┌──────────────▼──────────────────────┐
│  Specialists                        │
│  ├─ Data Explorer                   │
│  ├─ Hypothesis Analyst              │
│  └─ Graph Miner                     │
└──────────────┬──────────────────────┘
               │
      (Typed ExecutionResult)
               │
┌──────────────▼──────────────────────┐
│  Authority Plane                    │
│  ├─ Validate contracts              │
│  ├─ Admit state                     │
│  └─ Enforce validity                │
└─────────────────────────────────────┘
```

### Message Processing Sequence

```
User Input
  │
  ├─ Is command (/skill, /provider, /reload)?
  │  ├─ Yes: Handle command
  │  │        Update configuration
  │  │        Reload runtime
  │  │        Return status
  │  │
  │  └─ No: Continue
  │
  ├─ Build PlannerContext
  │  ├─ Load SessionFrame
  │  └─ Include ConversationHistory
  │
  ├─ Invoke Planner
  │  ├─ May request consultation
  │  │  ├─ Data Explorer (dataset info?)
  │  │  └─ Graph Miner (references?)
  │  │
  │  └─ Produce PlannerOutput
  │     ├─ messages: ModelMessages
  │     └─ result: PlannerResult
  │
  ├─ Add turn to ConversationHistory
  │
  └─ Present to user
```

### Execution Dispatch Sequence

```
Planner proposes Task
  │
  ├─ Create ExecutionRequest
  │  ├─ capability: enum value
  │  ├─ task: Task object
  │  └─ context: ExecutorContext
  │
  ├─ Dispatcher.dispatch(request)
  │  │
  │  ├─ Registry.resolve(capability)
  │  │  └─ Return provider instance
  │  │
  │  └─ provider.run(request)
  │     └─ Return ExecutionResult
  │
  ├─ Normalize ExecutionResult
  │  └─ Create PlannerWorkOutcome
  │
  ├─ Apply validity checks
  │
  └─ Authority decides next action
     ├─ Admit as Evidence
     ├─ Hold for review
     ├─ Reject with reason
     └─ Continue execution
```

---

## State Transitions and Validity

### The Authority Sequence

```
proposal
  ↓ (Human evaluation)
approval (Plan validation)
  ↓ (Authority validation)
execution (Specialist runs work)
  ↓ (Operator receives result)
observation (Result recorded)
  ↓ (Scientific validation)
Evidence admission (Admit to graph)
  ↓ (Hypothesis Analyst evaluation)
protected evaluation (Evaluate against hypothesis)
  ↓ (Governance review)
governance (Approve exact proposal)
  ↓ (Authority persists)
Discovery admission (Final claim admitted)
```

**Key Properties**:
- Each arrow is conditional
- Paths may end at any stage with typed result
- Completion does NOT imply Discovery
- No transition is mandatory
- Authority preserved at each boundary

### Validity Preservation

**Immutability**: FCOs frozen after creation
```python
class ImmutableCogniEDABaseModel(BaseModel):
    model_config = ConfigDict(frozen=True)
```

**Append-Only History**:
- ConversationTurn added but never modified
- ExecutionRun recorded immutably
- ObjectiveRevision captures all changes
- Supersession tracked, not deletion

**Lineage Tracking**:
- Every observation links to source
- Evidence links to Task and DataProfile
- Discovery links to Evidence set
- Provenance records causality

**Eligibility Checks**:
- Current-use status verified at retrieval
- Validity transitions tracked
- Staleness detected and managed
- Conflicting state flagged

---

## Component Interaction Patterns

### Workspace-First Initialization

```
Workspace.open(root)
  │
  ├─ Normalize path
  ├─ Create directories
  │  ├─ .cognieda/
  │  ├─ .cognieda/skills
  │  ├─ .cognieda/state
  │  ├─ .cognieda/sessions
  │  ├─ data/
  │  └─ AGENTS.md
  │
  ├─ Load project.toml
  │  └─ Parse providers
  │
  ├─ Verify directory structure
  └─ Return Workspace instance
```

### Provider Resolution

```
Workspace.project_config.resolve_model()
  │
  ├─ Validate default_provider exists
  ├─ Read provider profile
  │  ├─ type (openai/google/anthropic)
  │  ├─ model_name
  │  ├─ api_key_env
  │  └─ base_url
  │
  ├─ Get API key from environment
  │  └─ Raise MissingModelCredentialError if not set
  │
  └─ Return ModelConfig
```

### Agent Factory Pipeline

```
AgentFactory.create_agent()
  │
  ├─ Load tooling config
  │  ├─ Parse agents.toml
  │  ├─ Parse skills.toml
  │  └─ Parse mcp.toml
  │
  ├─ Load skills from directories
  ├─ Load MCP toolsets from servers
  │
  ├─ Choose model (OpenAI/Google/Anthropic)
  │  └─ Configure provider with API key
  │
  ├─ Assemble toolsets for worker
  ├─ Collect skills for worker
  │
  └─ Create PydanticAI Agent
     ├─ model
     ├─ toolsets
     ├─ capabilities (skills)
     └─ deps_type
```

### Execution Registry Pattern

```
ExecutorRegistry
  │
  ├─ register_provider(factory, capabilities)
  │  ├─ Validate factory is callable
  │  ├─ Validate capabilities not empty
  │  ├─ Check no duplicate capabilities
  │  └─ Store factory in _providers map
  │
  ├─ resolve(capability)
  │  ├─ Look up capability
  │  ├─ If not in _instances:
  │  │  ├─ Call factory()
  │  │  ├─ Validate result is ExecutorProvider
  │  │  └─ Cache in _instances
  │  │
  │  └─ Return cached instance
  │
  └─ list_capabilities()
     └─ Return tuple of registered capabilities
```

---

## Boundary Contracts

### ExecutionRequest Contract

```python
ExecutionRequest:
  capability: Capability        # What work?
  input: ExecutorInput
    task: Task                  # Which task?
  context: ExecutorContext      # What context?
    dataset_path: str | None    # Where is data?
    data_profile_id: UUID | None  # Profile reference?
```

### ExecutionResult Contract

```python
ExecutionResult:
  source_role: str              # Who provided this?
  task_id: UUID                 # For which task?
  work_id: str                  # Unique work ID
  status: ExecutionStatus       # SUCCEEDED/BLOCKED/FAILED
  limitations: list[str]        # What can't we claim?
  failure: ExecutionFailure | None  # If not succeeded
    code: str                   # Error category
    message: str                # Human-readable message
```

### PlannerWorkOutcome Contract

```python
PlannerWorkOutcome:
  source_role: str              # Data Explorer, etc.
  task_id: UUID
  work_id: str
  status: ExecutionStatus
  semantic_summary: str         # "X completed work Y"
  authoritative_refs: list[str] # References to Authority
  limitations: list[str]        # Known constraints
  blockers: list[str]           # Why can't we continue?
  permitted_next_actions: list[str]  # review_result, hold, replan
  result_digest: str            # SHA256 hash
```

---

## Configuration Evolution

### Startup Configuration

1. **Environment Variables** (process-level)
   - Override workspace defaults
   - Credentials from CI/CD
   - Database URL customization

2. **project.toml** (workspace-level)
   - Provider profiles
   - Model selection
   - Base URLs

3. **agents.toml** (worker configuration)
   - Skills per worker
   - MCP servers per worker

4. **skills.toml** (skill registration)
   - Directories
   - Validation options
   - Descriptions

5. **mcp.toml** (server configuration)
   - Transport type
   - Command and args
   - Environment variables

### Runtime Configuration Changes

```
/provider use openai
  │
  ├─ Workspace.use_provider("openai")
  │  ├─ Load project.toml
  │  ├─ Update default_provider
  │  └─ Save project.toml
  │
  ├─ Reload ProjectConfig in memory
  │
  └─ Application._reload_runtime(recreate_agent=True)
     ├─ Resolve new model config
     ├─ Create new AgentFactory
     ├─ Recreate Planner agent
     └─ Clear cached instances
```

---

## Error Handling and Recovery

### Execution Failure Handling

```
ExecutorProviderError
  │
  ├─ Captures capability
  ├─ Captures task_id
  ├─ Wraps original exception
  │
  └─ Propagates to Application
     ├─ Log error
     ├─ Create failure result
     ├─ Notify Planner
     └─ Present to user
```

### Model Credential Errors

```
MissingModelCredentialError
  │
  ├─ Raised during model resolution
  │
  ├─ Application catches
  │
  └─ Presents remediation message
     "Run '/provider key <provider>' to configure"
```

### Controlled Planner Errors

```
PlannerErrorCode:
  - INVALID_REQUEST (empty message)
  - MODEL_UNAVAILABLE (no credentials)
  - INVALID_MODEL_RESULT (validation failed)
```

---

## Extensibility Patterns

### Adding a Custom Capability

1. Add to `Capability` enum:
   ```python
   class Capability(StrEnum):
       MY_CAPABILITY = "my_capability"
   ```

2. Implement provider:
   ```python
   class MyProvider:
       async def run(self, request: ExecutionRequest) -> ExecutionResult:
           ...
   ```

3. Register during bootstrap:
   ```python
   registry.register_provider(
       lambda: MyProvider(),
       capabilities=(Capability.MY_CAPABILITY,)
   )
   ```

### Adding Custom Instructions

1. Create `AGENTS.md` in workspace root
2. Write custom Planner instructions
3. Run `/reload` to pick up changes
4. Instructions injected into Planner system prompt

### Adding Skills

1. Create skill functions using pydantic_ai_skills
2. Register in `skills.toml`:
   ```toml
   [my_skill]
   directories = ["./skills/my_skill"]
   ```
3. Assign to worker: `/skill use planner my_skill`

### Adding MCP Servers

1. Configure in `mcp.toml`:
   ```toml
   [my_server]
   transport = "stdio"
   command = "python"
   args = ["-m", "my_server"]
   ```
2. Assign to worker in `agents.toml`
3. Reload: `/reload`

---

## Testing Architecture

### Test Organization

```
tests/
  agents/
    planner/
      test_agent.py         # Planner unit tests
  cli/
    test_app.py            # CLI entrypoint tests
  conftest.py              # Pytest fixtures
```

### Fixture Patterns

- Workspace fixtures (temporary directories)
- Model config fixtures (mock configurations)
- Agent factory mocks (stub implementations)
- Dispatcher mocks (controlled execution)

### Contract Validation

- Schema validation tests (pydantic)
- Boundary contract tests
- State transition tests
- Authority boundary tests

---

## Performance Considerations

### Message History Management

- ConversationHistory grows with session
- Flattened for PydanticAI message_history
- May need pruning for long sessions
- Append-only design prevents deletion

### Provider Instance Caching

- Lazy instantiation via factory
- Reused across requests
- Stateless providers (safe to reuse)
- Clear/recreate on configuration change

### Database Transaction Boundaries

- commit_planner_operations() atomic
- All-or-nothing state transitions
- Retry on transient failures
- Idempotency via deduplication

---

## Security Considerations

### Credential Management

- API keys stored in workspace `.env`
- Never logged or serialized
- Environment variable passthrough
- Per-workspace isolation

### Authority Validation

- Every state transition validated
- Scientific authorship never assumed
- Persistence requires authority check
- Governance approval gated

### Input Validation

- All user input validated
- Schema validation on all state
- Type checking (mypy)
- Pydantic strict mode


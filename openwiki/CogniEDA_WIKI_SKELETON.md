# CogniEDA Wiki Skeleton

Complete wiki documentation structure for CogniEDA validity-preserving research-state infrastructure.

---

## Part 1: Concepts & Foundation

### 1.1 What is CogniEDA?

CogniEDA is **validity-preserving research-state infrastructure** for analytical and scientific investigation.

**Core Problem**: Conversations and model outputs don't reliably distinguish between:
- Planning ideas
- User-supplied assumptions
- Observed results
- Evaluated claims
- Stale findings

**Solution**: CogniEDA treats research state as **governed state**, not remembered prose. It keeps investigation explicit, traceable, restrained, and safe to resume across sessions.

**Architectural Priorities** (in order):
1. Conclusion validity and traceability
2. Context type safety
3. Multi-session continuity
4. Speed and convenience

**What It's NOT**: Not a chatbot, autonomous scientist, generic multi-agent framework, vector-memory wrapper, or unrestricted analysis agent.

### 1.2 Research State Separation

CogniEDA maintains eight distinct First-Class Objects (FCOs):

**Semantic Knowledge Graph** (4 FCOs):
- Objective → Hypothesis → Evidence → Discovery

**Additional FCOs** (4):
- DataProfile (immutable dataset snapshot)
- Assumption (planning-only statement)
- Task (semantic work identity)
- SessionFrame (active context membership)

**Key Property**: Epistemic roles are independent of persistence. A persisted record is not automatically scientific knowledge.

### 1.3 Authority & Governance

| Authority | Holder | Decides | Cannot Acquire |
|-----------|--------|---------|-----------------|
| Human | Via Planner | Intent, plan approval, clarification | Executor access, scientific authorship |
| Planning | Planner | Objective coordination, Task DAG proposals | Scientific operationalization |
| Execution | Specialist | Role-specific operation | Admission, governance |
| Scientific | Hypothesis Analyst | Protocol, protected evaluation | Dataset access, persistence |
| Governance | Authorized review | Approve/reject proposals | Rewrite content |
| Admission | Application authority | Validate contracts, persist | Scientific interpretation |
| Persistence | Application authority | Transaction ordering, replay | Scientific authorship |
| Validity-transition | Authorized boundary | Change eligibility | Rewrite Evidence |

### 1.4 The Validity Sequence

```
proposal != approval != execution != observation != Evidence admission !=
  protected evaluation != governance != Discovery admission
```

Each step is conditional. Paths may end at any stage with a typed result, blocker, rejection, or non-completion. Completion does NOT imply a Discovery.

---

## Part 2: System Architecture

### 2.1 Three Cooperating Planes

**Control Plane**: Human + Planner coordinate intent, planning, session management
**Specialist Plane**: Data Explorer, Hypothesis Analyst, Graph Miner execute bounded work
**Authority Plane**: Application authority, governance validate and persist state

```
Human <---> Planner (ONLY boundary)
              ↓
      Application coordination
              ↓
    Data Explorer / HA / Graph Miner
              ↓
    Application Authority + Governance
              ↓
         Total Persistence
```

**Critical**: Specialists never communicate directly with humans. All user interaction flows through the Planner.

### 2.2 Component Responsibilities

#### Control Plane

**Planner**:
- Coordinates research work without acquiring scientific authorship
- Proposes complete Plan candidates with Task DAGs
- May consult Data Explorer or Graph Miner for planning info
- Explains reasoning, presents limitations
- Manages SessionFrame coordination
- **Never**: Writes semantic graph, scientific, or provenance state

**Application**:
- Orchestrates user interaction and message handling
- Routes commands (/skill, /provider, /reload)
- Builds PlannerContext
- Invokes Planner with conversation history
- Presents results to user
- Reloads runtime on configuration changes

**Workspace**:
- Manages file system and configuration lifecycle
- Persists: project.toml, agents.toml, skills.toml, mcp.toml, AGENTS.md, .env
- Methods: open(), initialize(), load/save configs, manage skills/providers

#### Specialist Plane

**Data Explorer**:
- Profiles and analyzes datasets deterministically
- Returns typed observations (NOT Evidence)
- Cannot create Evidence directly; requires admission

**Hypothesis Analyst** (deferred):
- Target: Scientific operationalization and protected evaluation
- Feasibility assessment, protocol content, Evidence obligations
- Currently: Stub implementation

**Graph Miner** (deferred):
- Target: Read-only semantic graph inquiry
- Return references, paths, gaps, contradictions, validity
- Currently: NotImplementedError

#### Authority Plane

**ExecutorDispatcher**:
- Routes capability requests to registered providers
- Fails closed on missing capability or provider error

**ExecutorRegistry**:
- Lazy registry for capability-based dispatch
- Validates registrations (no duplicates, factories callable)

**Admission Boundary**:
- `commit_planner_operations()` - Atomic transaction for state transitions
- Validates approval state before commit
- All-or-nothing: succeeds or rolls back

### 2.3 Data Flow Diagrams

#### User Message Processing Flow

```
1. User Input
   ↓
2. Application.submit_message()
   ├─ Check if command (/skill, /provider, /reload)
   │  ├─ If yes: Handle command, reload runtime
   │  └─ Return result
   │
   └─ If not command:
      ├─ Build PlannerContext (SessionFrame + ConversationHistory)
      ├─ Invoke Planner agent
      │  ├─ Planner reasons over task
      │  ├─ May request consultation:
      │  │  ├─ Data Explorer (dataset info?)
      │  │  └─ Graph Miner (references?)
      │  └─ Generate: response OR plan OR request OR continue
      ├─ Add turns to ConversationHistory
      └─ Present result to user
```

#### Specialist Execution Flow

```
1. Planner proposes Task
   ↓
2. Create ExecutionRequest
   ├─ capability: DATA_PROFILING
   ├─ task: {task_id, instruction, ...}
   └─ context: {dataset_path, data_profile_id}
   ↓
3. Dispatcher.dispatch(request)
   ├─ Resolve capability → provider
   └─ Dispatch to provider
   ↓
4. Data Explorer.run(request)
   ├─ Load dataset
   ├─ Analyze/profile
   └─ Return ExecutionResult
   ↓
5. Normalize to PlannerWorkOutcome
   ├─ Extract status, work_id, summary
   └─ Compute result digest
   ↓
6. Authority Decision
   ├─ Admit as Evidence?
   ├─ Hold for review?
   ├─ Reject?
   └─ Continue execution?
```

---

## Part 3: Data Model & Persistence

### 3.1 First-Class Objects (FCOs)

**Objective**
- UUID, text
- Research intent for investigation
- Scoped container for Tasks

**DataProfile**
- UUID, row_count, column_count, columns
- Immutable snapshot of dataset structure
- Validity-tracked

**Assumption**
- UUID, text
- Planning-only statement (never empirical)
- Cannot become Evidence

**Task**
- UUID, objective_id, kind (DATA/SCIENTIFIC/GRAPH), instruction, status
- Semantic work identity (not execution schedule)
- Objective-scoped

**Hypothesis**
- Scientific claim to test
- Protocol and method defined
- Evidence obligations tracked

**Evidence**
- Directly observed analytical result
- Immutable content
- Lineage and source tracked

**Discovery**
- Final admitted claim with evaluation
- Epistemic status: SUPPORTED/CONTRADICTED/INCONCLUSIVE
- Governance-approved

**SessionFrame**
- Active context membership snapshot
- Outside semantic graph
- Captures session state for restart

### 3.2 Non-FCO Persisted Entities

- **Plan** - Immutable aggregate (objective, assumptions, tasks, dependencies)
- **PlannerOperation** - Mutation envelope for state transitions
- **ExecutionRun** - Attempt identity and metadata
- **ExecutionOutbox** - Dispatch intent paired with attempt
- **AnalysisFrame** - Workflow context
- **ObjectiveRevisionRecord** - Objective change history
- **UserDecisionRecord** - User decisions for provenance

### 3.3 Persistence Model

**Database**: SQLModel ORM on SQLite (configurable via COGNIEDA_DB_URL)

**Pattern**:
- Immutable records (append-only, never updated)
- One repository per entity type
- CRUD and query methods
- Transactional boundaries for state transitions

**Admission Boundary**:
- `commit_planner_operations()` validates approval state
- Atomic all-or-nothing transaction
- Records provenance (changed_fields, reason, node_name)

---

## Part 4: Configuration System

### 4.1 Workspace Structure

```
workspace/
  .cognieda/
    project.toml       (provider config)
    agents.toml        (worker skills/MCP)
    skills.toml        (skill definitions)
    mcp.toml           (MCP servers)
    state/             (operational state)
    sessions/          (session artifacts)
  data/                (datasets)
  AGENTS.md            (agent instruction)
  .env                 (credentials)
```

### 4.2 Configuration Files

**project.toml** - Provider and model configuration
```toml
default_provider = "google"

[providers.google]
type = "google"
model = "gemini-2.5-flash"
api_key_env = "GOOGLE_API_KEY"
base_url = ""  # optional

[providers.openai]
type = "openai"
model = "gpt-5"
api_key_env = "OPENAI_API_KEY"

[providers.anthropic]
type = "anthropic"
model = "claude-sonnet-4"
api_key_env = "ANTHROPIC_API_KEY"
```

**agents.toml** - Worker configuration
```toml
[planner]
# skills = ["memory_management", "task_planning"]
# mcp = ["filesystem"]

[data_explorer]
# skills = []
# mcp = []
```

**skills.toml** - Skill registration
```toml
[memory_management]
directories = ["./skills/memory"]
description = "Manage session frames and assumptions"
defer_loading = false
validate = true
```

**mcp.toml** - MCP server configuration
```toml
[filesystem]
transport = "stdio"
command = "uvx"
args = ["mcp-server-filesystem"]

[neo4j]
transport = "http"
url = "http://localhost:8000/mcp"
```

### 4.3 Environment Variables

- **GOOGLE_API_KEY**, **OPENAI_API_KEY**, **ANTHROPIC_API_KEY** - Model credentials
- **COGNIEDA_DB_URL** - Custom database URL (default: workspace-local SQLite)
- **COGNIEDA_MODEL_PROVIDER** - Override default provider

Loaded from workspace `.env` file (created on first Workspace.open()).

### 4.4 Runtime Reload

`Application._reload_runtime()` supports:
- `reload_tooling=True` - Reload skills and MCP toolsets
- `reload_instruction=True` - Reload agent instructions from AGENTS.md
- `recreate_agent=True` - Recreate agent instance with new config

---

## Part 5: Runtime & Execution

### 5.1 Bootstrap Sequence

1. Parse CLI args (--mode, path)
2. `_load_workspace_environment(path)` - Load/create .env
3. `Workspace.open(path)` - Initialize directories, load configs
4. Resolve model configuration from project.toml
5. Create `AgentFactory` (load tooling config)
6. Initialize `ExecutorRegistry` with providers
   - Register `DataExplorer` with DATA_* capabilities
7. Create `Planner` (assemble instructions)
8. Assemble `Application` instance
9. Launch `REPL(app, renderer)`

### 5.2 Message Processing Loop

1. User enters text at REPL prompt
2. Check if command (starts with "/")
   - `/skill add|rm|list|use|drop`
   - `/provider list|use|model|key`
   - `/reload`
3. Build `PlannerContext` (SessionFrame + ConversationHistory)
4. Invoke `planner_agent.run(message, context)`
5. Capture `PlannerOutput` (messages + result)
6. Add turn to `ConversationHistory`
7. Present result to user

### 5.3 Planning Consultation Workflow

1. Planner frames planning need
2. If dataset info required:
   a. Create `ExecutionRequest` (DATA_PROFILING capability)
   b. `Dispatcher.dispatch(request)`
   c. `DataExplorer.run()` - Profile dataset
   d. Return `ExecutionResult`
   e. Normalize to `PlannerWorkOutcome`
3. Planner uses consultation in planning context
4. Planner generates Plan candidate
5. Return complete `PlannerResult`

### 5.4 Skill Management Commands

```
/skill add NAME DIRECTORY
  → Workspace.add_skill() (update skills.toml)
  → Application._reload_runtime(reload_tooling=True)
  → AgentFactory.reload_tooling()
  → Recreate agent

/skill use WORKER SKILL
  → Workspace.add_worker_skill() (update agents.toml)
  → Application._reload_runtime(reload_tooling=True, recreate_agent=True)

/skill drop WORKER SKILL
  → Workspace.remove_worker_skill()
  → Reload runtime
```

### 5.5 Provider Configuration Commands

```
/provider list
  → Display registered providers

/provider use PROFILE
  → Workspace.use_provider() (update project.toml)
  → Application._reload_runtime(recreate_agent=True)
  → Resolve new model config
  → Recreate Planner agent

/provider model PROFILE MODEL
  → Workspace.set_provider_model()
  → Reload runtime

/provider key PROFILE
  → Prompt user for API key (input())
  → Workspace.set_provider_api_key()
  → Update .env
  → Reload runtime
```

---

## Part 6: Agent Specializations

### 6.1 Planner Agent

**Role**: Control plane coordinator, human-facing reasoning agent

**Responsibilities**:
- Frame planning needs
- Propose complete Plan candidates
- Construct Task DAGs
- Request consultant input (optional)
- Present limitations and blockers
- Ask for clarification/correction

**Boundaries**:
- Never writes semantic graph, scientific, or provenance state
- Never acquires scientific authorship or Evidence creation authority
- Proposes only; Application authority validates and persists

**Input**: User message + PlannerContext (SessionFrame + ConversationHistory)

**Output**: PlannerResult
- `plan` - Candidate Plan (or None)
- `tasks` - Task tuple (or empty)
- `response` - Text response (or None)
- `human_input_request` - Request for user input (or None)
- `continue_execution` - Boolean flag for execution continuation

**Instruction Assembly**:
- Load base instructions from built-in `plan_or_answer.txt`
- Optionally inject custom instructions from workspace `AGENTS.md`
- Compose into agent system prompt

### 6.2 Data Explorer

**Role**: Specialist provider for data analysis

**Responsibilities**:
- Profile datasets
- Analyze data quality
- Transform data (deferred)
- Return observations (NOT Evidence)

**Boundaries**:
- Cannot create Evidence directly
- Requires admission for observation → Evidence transition
- Restart-safe provider (stateless)

**Capabilities**:
- DATA_PROFILING
- DATA_ANALYSIS
- DATA_TRANSFORMATION

**Methods**:
- `profile_dataset()` - Generate dataset profile
- `execute_analysis()` - Run analysis on dataset
- `analyze_dataset()` - High-level analysis tool

### 6.3 Hypothesis Analyst (Deferred)

**Role**: Scientific operationalization and protected evaluation

**Target Responsibilities**:
- Assess hypothesis feasibility
- Define protocol and method
- Track Evidence obligations
- Perform protected evaluation
- Produce scientific proposals

**Current Status**: Scaffold implementation (stub graph, not executable)

**Capability**:
- HYPOTHESIS_TESTING

### 6.4 Graph Miner (Deferred)

**Role**: Read-only semantic graph inquiry

**Target Responsibilities**:
- Query existing Objective references
- Return paths and dependencies
- Identify gaps and contradictions
- Validate object validity

**Current Status**: NotImplementedError

**Capability**:
- GRAPH_MINING

---

## Part 7: Extension Points

### 7.1 Custom Agent Instructions

Place markdown in `workspace/AGENTS.md`. Will be loaded and injected into Planner system prompt on startup and `/reload`.

### 7.2 Skills Integration

1. Implement skill functions via pydantic_ai_skills
2. Register in skills.toml:
   ```toml
   [my_skill]
   directories = ["./skills/my_skill"]
   ```
3. Assign to worker via `/skill use WORKER my_skill`

### 7.3 MCP Server Integration

1. Configure server in mcp.toml:
   ```toml
   [my_server]
   transport = "stdio"
   command = "python"
   args = ["-m", "my_mcp_server"]
   ```
2. Assign to worker in agents.toml:
   ```toml
   [planner]
   mcp = ["my_server"]
   ```

### 7.4 Model Provider Support

Supported: OpenAI, Google, Anthropic

To add provider:
1. Modify `infrastructure/llm/factory.py:_choose_model()`
2. Implement provider initialization
3. Update project.toml defaults

### 7.5 Custom Specialist Provider

1. Implement `ExecutorProvider` protocol:
   ```python
   async def run(self, request: ExecutionRequest) -> ExecutionResult
   ```
2. Register with dispatcher:
   ```python
   registry.register_provider(
       lambda: MyProvider(),
       capabilities=(Capability.MY_CAPABILITY,)
   )
   ```
3. Add Capability to enum if needed

### 7.6 Database Customization

- Set `COGNIEDA_DB_URL` to different SQLAlchemy connection string
- Or extend SQLModel models in `infrastructure/persistence/models.py`

---

## Part 8: Execution Model

### 8.1 Capability-Based Dispatch

**Capability Enum**:
- DATA_ANALYSIS
- DATA_PROFILING
- DATA_TRANSFORMATION
- HYPOTHESIS_TESTING
- GRAPH_MINING

**Dispatch Pattern**:
1. Planner determines work needs
2. Create `ExecutionRequest` with capability
3. `ExecutorRegistry.resolve(capability)` → provider instance
4. `ExecutorDispatcher.dispatch(request)` → provider.run()
5. Return `ExecutionResult` (typed, normalized)

### 8.2 Execution Contracts

**ExecutionRequest**:
- `capability` - Requested capability
- `input` - Task + role-native parameters
- `context` - Dataset path, profile ID, other context

**ExecutionResult**:
- `source_role` - Provider role name
- `task_id` - Task UUID
- `work_id` - Unique work identifier
- `status` - SUCCEEDED, BLOCKED, FAILED
- `limitations` - Known limitations of result
- `failure` - Error details (if not succeeded)

**ExecutorProvider** (Protocol):
- `async def run(request: ExecutionRequest) -> ExecutionResult`
- Must be restart-safe (stateless or replay-safe)
- Must validate input and fail closed

### 8.3 Task Kinds

- **DATA** - Data analysis, profiling, transformation
- **SCIENTIFIC** - Hypothesis testing, evaluation
- **GRAPH** - Semantic graph inquiry

Task kind may constrain authority and tool access but does NOT determine routing table or execution strategy.

---

## Part 9: Current Implementation Status

### Fully Implemented ✅

- Core schemas and FCO definitions (all 8 FCOs)
- Immutable Plan domain and validation
- Append-only ConversationHistory
- Workspace filesystem management
- Provider configuration system (OpenAI, Google, Anthropic)
- Model factory and agent creation
- ExecutorRegistry and ExecutorDispatcher
- Data Explorer deterministic operations
- Direct Task-to-Evidence admission pathway (MVP transitional)
- SQLModel persistence seams (SQLite verified)
- Planner REPL scaffold
- Command handling (/skill, /provider, /reload)

### Partially Implemented 🔶

- Hypothesis Analyst (scaffold with stub graph)
- Graph Miner (read-only stub, not executable)
- PlannerOperation commit transaction (foundation exists)

### Deferred ❌

- Human approval workflow and decision modes
- Plan activation and active Task selection
- Task DAG runtime execution
- Scientific investigation protocol
- Protected hypothesis evaluation
- Governance review and Discovery admission
- Semantic graph query interface
- Restart-safe session continuity
- Multi-session resume
- Validity transition service
- DVC data versioning integration

### MVP-v2 Definition of Done

A complete scientific research loop including:
1. Plan proposal and human approval
2. Task execution and Evidence admission
3. Hypothesis testing and evaluation
4. Discovery admission through governance
5. Restart and grounded follow-up

---

## Part 10: API Reference

### Key Classes

**Application** (runtime/application.py)
- `submit_message(message: str) -> Message`
- `_handle_command(command: str) -> Message`
- `_reload_runtime(reload_tooling, reload_instruction, recreate_agent)`

**Workspace** (runtime/workspace.py)
- `Workspace.open(root) -> Workspace`
- `Workspace.initialize(root)`
- `load_agents_config()`, `save_agents_config()`
- `load_skills_config()`, `save_skills_config()`
- `add_skill()`, `remove_skill()`
- `add_worker_skill()`, `remove_worker_skill()`
- `use_provider()`, `set_provider_model()`, `set_provider_api_key()`

**ExecutorDispatcher** (execution/dispatcher.py)
- `async dispatch(request: ExecutionRequest) -> ExecutionResult`

**ExecutorRegistry** (execution/registry.py)
- `register_provider(factory, capabilities)`
- `resolve(capability) -> ExecutorProvider`
- `list_capabilities()`

**Planner** (agents/planner/agent.py)
- `async run(request: str, context: PlannerContext) -> PlannerOutput`
- `async reload(model_config, agent_instruction, recreate_agent)`

**DataExplorer** (agents/data_explorer/agent.py)
- `async run(request: ExecutionRequest) -> ExecutionResult`

### Key Schemas

**Objective** (schemas/artifacts.py)
- `objective_id: UUID`
- `text: NonEmptyStr`

**Task** (schemas/artifacts.py)
- `task_id: UUID`
- `objective_id: UUID`
- `kind: TaskKind` (DATA, SCIENTIFIC, GRAPH)
- `instruction: NonEmptyStr`
- `status: TaskStatus`

**Plan** (schemas/plan.py)
- `plan_id: UUID`
- `objective: Objective`
- `assumptions: tuple[Assumption, ...]`
- `task_ids: tuple[UUID, ...]`
- `dependencies: tuple[PlanDependency, ...]`

**PlannerResult** (agents/planner/types.py)
- `plan: Plan | None`
- `tasks: tuple[Task, ...]`
- `response: str | None`
- `human_input_request: str | None`
- `continue_execution: bool`

---

## Part 11: Development

### Setup

```bash
# Prerequisites: Python 3.12+, uv
uv sync
uv tool install --editable .
copy .env.example .env
```

### Configuration

1. Set model API key in `.env`:
   ```
   GOOGLE_API_KEY=your_key_here
   ```

2. Create workspace:
   ```bash
   cognieda
   ```

3. Configure provider (optional):
   ```
   COGNIEDA_MODEL_PROVIDER=openai
   ```

### Testing

```bash
uv run pytest                 # Run all tests
uv run ruff check .           # Lint
uv run mypy src/cognieda      # Type check
```

### Debugging

- Enable debug logging
- Use workspace mock mode: `cognieda --mode mock`
- Inspect `.cognieda/` directory for configuration and state

---

## Part 12: Roadmap & Status

See `/docs/status/current-state.md` for:
- Dated implementation boundary
- Evidence-qualified capability claims
- Blocked work and dependencies
- Known limitations

MVP-v2 target includes complete end-to-end scientific loop with governance and Discovery admission.

---

**Report Generated**: 2026-08-14T17:52:45.850Z  
**Investigation Scope**: 50+ source files, configs, and architecture docs  
**Status**: Foundation implemented, deferred = end-to-end orchestration

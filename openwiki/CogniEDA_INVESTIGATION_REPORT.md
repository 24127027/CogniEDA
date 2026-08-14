# CogniEDA Deep Source Investigation Report

**Investigation Date**: 2026-08-14  
**Scope**: Complete architecture, components, data flow, agents, persistence, configuration, workflows, extension points  
**Status**: Comprehensive analysis of 50+ source files, configs, and documentation

---

## 1. MAIN PURPOSE & DESIGN PHILOSOPHY

### Core Mission
**CogniEDA is validity-preserving research-state infrastructure** for analytical and scientific investigation. It explicitly separates research intent, planning state, data state, scientific commitments, observations, claims, validity, provenance, and active context.

### Why It Matters
Conversations and model outputs don't reliably record whether a sentence is:
- A planning idea
- A user-supplied assumption  
- An observed result
- An evaluated claim
- A finding that has become stale

CogniEDA treats research state as **governed state**, not remembered prose. It keeps investigation traceable, restrained, and safe to resume across sessions.

### Architectural Priorities (in order)
1. **Conclusion validity and traceability** (epistemic correctness first)
2. **Context type safety**
3. **Multi-session continuity**
4. **Speed and convenience** (last)

### What It Is NOT
- A chatbot
- An autonomous scientist
- A generic multi-agent framework
- A vector-memory wrapper
- An unrestricted analysis agent

---

## 2. SYSTEM ARCHITECTURE & BOUNDARIES

### Three Cooperating Planes

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

### Human Interaction Boundary
All user interaction flows through **Human ↔ Planner** only. Specialists never communicate directly with humans.

### Authority Taxonomy

| Authority | Holder | Can Decide/Perform | Cannot Acquire |
|-----------|--------|-------------------|-----------------|
| Human | Human via Planner | Intent, plan approval, clarification | Executor access, scientific authorship |
| Planning | Planner | Objective coordination, Task DAG proposals | Scientific operationalization, Evidence |
| Execution | Bounded specialist | Role-specific operation, return result | Admission, governance, scope expansion |
| Scientific | Hypothesis Analyst | Feasibility, protocol, protected evaluation | Dataset access, governance, persistence |
| Governance | Authorized review | Approve/reject/hold proposals | Rewrite content, make durable |
| Admission | Application authority | Validate contracts, durable transitions | Scientific interpretation |
| Persistence | Application authority | Transaction ordering, idempotency, replay | Scientific authorship, governance |
| Validity-transition | Authorized boundary | Change eligibility, preserve truth | Rewrite Evidence/Discovery |

---

## 3. MAJOR COMPONENTS & RESPONSIBILITIES

### 3.1 Runtime Layer (`src/cognieda/runtime/`)

#### Application
- **Orchestrates** user interaction, message handling, command routing
- **Manages**: workspace, planner_agent, dispatcher, session_frame, conversation_history
- **Accepts** user messages, builds context, invokes Planner
- **Handles** commands: `/skill`, `/provider`, `/reload`
- **Presents** results to user; reloads runtime on config changes

#### Bootstrap
- **Initializes** entire system
- **Flow**: Load .env → Open Workspace → Resolve model config → Create AgentFactory → Register providers → Create Planner → Assemble Application

#### Workspace
- **Manages** file system and configuration lifecycle
- **Owns** directories: `.cognieda/`, `data/`, `sessions/`, `state/`
- **Persists**: project.toml (providers), agents.toml (workers), skills.toml, mcp.toml, AGENTS.md, .env
- **Methods**: open(), initialize(), load/save configs, manage skills, manage providers, set API keys

#### ConversationHistory
- **Append-only** message history for LLM context
- **Structure**: List of ConversationTurn, each containing ModelMessages
- **Purpose**: Maintain conversation state across Planner invocations

### 3.2 CLI & Entrypoints

- **app.py**: Parse args, choose mode (real/mock), bootstrap, launch REPL
- **main.py**: Async REPL loop - read input, render, submit to Application
- **Renderer**: Format and display messages

### 3.3 Agents

#### Planner (Control Plane)
- **Coordinates** research work without acquiring scientific authorship
- **Proposes** complete Plan candidates with Task DAGs
- **May consult** Data Explorer or Graph Miner for planning info
- **Explains** reasoning, presents limitations, asks for clarification
- **Manages** SessionFrame and GeneratedView coordination
- **Never**: Writes semantic graph, scientific, or provenance state directly

#### Data Explorer (Specialist)
- **Profiles** and analyzes datasets deterministically
- **Returns** typed observations (not Evidence)
- **Cannot** create Evidence directly; requires admission

#### Hypothesis Analyst (Specialist - Deferred)
- **Scaffold** for scientific operationalization and protected evaluation
- **Target**: Feasibility, hypothesis content, Evidence obligations, protected evaluation
- **Currently**: Stub implementation

#### Graph Miner (Specialist - Deferred)
- **Read-only** semantic graph inquiry
- **Target**: Return references, paths, gaps, contradictions, validity
- **Currently**: NotImplementedError

### 3.4 Execution Layer

#### ExecutorDispatcher
- **Routes** capability requests to registered providers
- **Dispatches** ExecutionRequest → ExecutionResult
- **Fails closed** on missing capability or provider error

#### ExecutorRegistry
- **Lazy registry** for capability-based dispatch
- **Methods**: register_provider(factory, capabilities), resolve(capability)
- **Validation**: No duplicate capabilities, factories must be callable

#### Contracts
- `ExecutionRequest` - Capability + Task + Context
- `ExecutionResult` - Status (SUCCEEDED/BLOCKED/FAILED) + work_id + limitations
- `ExecutorProvider` - Protocol: `async run(request) → result`
- `PlannerWorkOutcome` - Normalized for Planner consumption

#### Capabilities
- DATA_ANALYSIS, DATA_PROFILING, DATA_TRANSFORMATION, HYPOTHESIS_TESTING, GRAPH_MINING

### 3.5 Application Layer

- **Ports**: ExecutorDispatcher, AgentFactory, ToolingConfig, ModelConfig
- **Services**: planner_commit (atomic transitions), plan_validation, execution_admission, transition_service

### 3.6 Infrastructure Layer

#### LLM Factory
- Choose model by provider (OpenAI/Google/Anthropic)
- Configure with API key + base URL
- Load toolsets and skills
- Create PydanticAI Agent

#### Agent Tooling Manager
- Load agents.toml, skills.toml, mcp.toml
- Load MCP toolsets and skills from directories
- Support runtime reload

#### Persistence
- **ORM**: SQLModel (Pydantic + SQLAlchemy)
- **DB**: SQLite by default (COGNIEDA_DB_URL configurable)
- **Repositories**: One per entity type with CRUD/query methods
- **Pattern**: Immutable records, append-only history, transactional boundaries

---

## 4. FIRST-CLASS OBJECTS (FCOs)

### Semantic Knowledge Graph (4 FCOs)
```
Objective → Hypothesis → Evidence → Discovery
```

### All FCOs (8 total)
1. **Objective** - Research intent
2. **DataProfile** - Immutable dataset snapshot
3. **Assumption** - Planning-only statement
4. **Task** - Semantic work identity (kind: DATA/SCIENTIFIC/GRAPH)
5. **Hypothesis** - Claim to test
6. **Evidence** - Observed analytical result
7. **Discovery** - Final admitted claim
8. **SessionFrame** - Active context membership (outside graph)

### Properties
- Immutable (frozen after creation)
- Identifiable (UUID)
- Traceable (provenance + lifecycle)
- Validity-aware (current-use eligibility)

---

## 5. DATA FLOW & MESSAGE PROCESSING

### User Message Flow
```
User Input → Application.submit_message()
  → Check command vs text
  → Build PlannerContext (SessionFrame + ConversationHistory)
  → Invoke Planner agent
  → Planner may request consultation (Data Explorer/Graph Miner)
  → Planner returns: response OR plan OR request OR continue
  → Add to ConversationHistory
  → Present to user
```

### Specialist Execution Flow
```
Planner proposes Task
  → Create ExecutionRequest (capability + task + context)
  → Dispatcher.dispatch(request)
  → Provider executes (role-native)
  → Return ExecutionResult (status + work_id + provenance)
  → Normalize to PlannerWorkOutcome
  → Authority decides: admit as Evidence? Hold? Reject?
```

### Authority Sequence
```
proposal → approval → execution → observation → Evidence admission → 
  evaluation → governance → Discovery admission
```
Each step is conditional; paths end at any stage with typed result.

---

## 6. SCHEMAS & DATA MODELS

### Key Enums
- **ObjectType**: OBJECTIVE, DATA_PROFILE, ASSUMPTION, TASK, HYPOTHESIS, EVIDENCE, DISCOVERY, SESSION_FRAME
- **TaskStatus**: PENDING, RUNNING, COMPLETED, FAILED
- **TaskKind**: DATA, SCIENTIFIC, GRAPH
- **ExecutionRunStatus**: PENDING_APPROVAL, ADMITTED, DISPATCH_CLAIMED, RUNNING, DISPATCH_FAILED, EXECUTION_FAILED, EXPIRED, ABANDONED, CANCELLED
- **DiscoveryEpistemicStatus**: SUPPORTED, CONTRADICTED, INCONCLUSIVE, INSUFFICIENT_EVIDENCE
- **PlannerOperationType**: CREATE_OBJECTIVE_REVISION, UPDATE_OBJECTIVE, CREATE_ASSUMPTION, UPDATE_ASSUMPTION_STATE, CREATE_HYPOTHESIS, CREATE_EXECUTION_RUN, CREATE_EXECUTION_OUTBOX, CREATE_EVIDENCE, CREATE_DISCOVERY, UPDATE_SESSION_FRAME, FLAG_OBJECT

### Core Models
- **Objective**: UUID, text
- **DataProfile**: UUID, row_count, column_count, columns
- **Assumption**: UUID, text
- **Task**: UUID, objective_id, kind, instruction, status
- **Plan**: plan_id, objective, assumptions, task_ids, dependencies (immutable, non-FCO)
- **PlanDependency**: prerequisite_task_id, dependent_task_id

---

## 7. PERSISTENCE MODEL

### Database
- **ORM**: SQLModel
- **Default**: SQLite (configurable via COGNIEDA_DB_URL)
- **Append-Only**: Immutable records never updated

### Persisted Records
- FCOs: ObjectiveRecord, DataProfileRecord, AssumptionRecord, TaskRecord, HypothesisRecord, EvidenceRecord, DiscoveryRecord, SessionFrameRecord
- Operations: PlannerOperationRecord, ExecutionRunRecord, ExecutionOutboxRecord, ExecutionApprovalRecord
- Provenance: ObjectiveRevisionRecord, UserDecisionRecord, validity events
- Support: AnalysisFrameRecord, lease/cache records

### Admission Boundary
- `commit_planner_operations()` - Atomic transaction for state transitions
- Validates approval state before commit
- All-or-nothing: succeeds or rolls back

---

## 8. CONFIGURATION SYSTEM

### File-Based Configuration

#### project.toml (Provider Config)
```toml
default_provider = "google"

[providers.google]
type = "google"
model = "gemini-2.5-flash"
api_key_env = "GOOGLE_API_KEY"
```

#### agents.toml (Worker Configuration)
```toml
[planner]
# skills = ["memory_management"]
# mcp = ["filesystem"]
```

#### skills.toml (Skill Registration)
```toml
[memory_management]
directories = ["./skills/memory"]
```

#### mcp.toml (MCP Servers)
```toml
[filesystem]
transport = "stdio"
command = "uvx"
args = ["mcp-server-filesystem"]
```

### Environment Variables
- **Model credentials**: GOOGLE_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY
- **Custom DB**: COGNIEDA_DB_URL
- **Provider override**: COGNIEDA_MODEL_PROVIDER
- **Location**: workspace/.env (created on first Workspace.open())

### Runtime Reload
- `Application._reload_runtime()` supports:
  - `reload_tooling=True` - Reload skills/MCP
  - `reload_instruction=True` - Reload agent instructions
  - `recreate_agent=True` - Recreate agent instance

---

## 9. KEY WORKFLOWS

### 1. Application Bootstrap
1. Parse CLI args (--mode, path)
2. Load workspace environment (.env)
3. Open workspace (create dirs, load configs)
4. Resolve model configuration
5. Create AgentFactory (load tooling)
6. Register ExecutorRegistry (DataExplorer)
7. Create Planner (assemble instructions)
8. Return Application instance
9. Launch REPL(app, renderer)

### 2. Message Processing
1. Check if command ("/skill", "/provider", "/reload")
2. If not command: Build PlannerContext (SessionFrame + ConversationHistory)
3. Invoke planner_agent.run(message, context)
4. Capture PlannerOutput (messages + result)
5. Add turns to ConversationHistory
6. Present result to user

### 3. Planning Consultation
1. Planner frames planning need
2. If requires dataset info:
   - Create ExecutionRequest (DATA_PROFILING capability)
   - Dispatcher.dispatch()
   - DataExplorer loads and profiles dataset
   - Return typed result
   - Application normalizes → PlannerWorkOutcome
3. Planner uses consultation in planning context
4. Planner generates Plan candidate
5. Return complete PlannerResult

### 4. Skill Management
```
/skill add NAME DIRECTORY
  → Workspace.add_skill() (update skills.toml)
  → Application._reload_runtime(reload_tooling=True)
  → AgentFactory.reload_tooling()
  → Recreate agent with new capabilities

/skill use WORKER SKILL
  → Workspace.add_worker_skill() (update agents.toml)
  → Application._reload_runtime(reload_tooling=True, recreate_agent=True)
```

### 5. Provider Configuration
```
/provider use PROFILE
  → Workspace.use_provider()
  → Update default_provider in project.toml
  → Application._reload_runtime(recreate_agent=True)
  → Resolve new model config
  → Recreate Planner agent

/provider key PROFILE
  → Prompt for API key
  → Workspace.set_provider_api_key()
  → Update .env
  → Application._reload_runtime(recreate_agent=True)
```

---

## 10. EXTENSION POINTS

1. **Custom Instructions**: Place markdown in `workspace/AGENTS.md`
2. **Skills**: Implement via pydantic_ai_skills, register in skills.toml
3. **MCP Servers**: Define in mcp.toml
4. **Model Providers**: Modify `infrastructure/llm/factory.py`
5. **Data Loading**: Extend `infrastructure/datasets/loaders.py`
6. **Specialist Providers**: Implement ExecutorProvider, register with dispatcher
7. **Database**: Set COGNIEDA_DB_URL to different SQLAlchemy URL
8. **Commands**: Extend `Application._handle_command()`
9. **Planner Behavior**: Customize via AGENTS.md
10. **Execution Dispatch**: Add Capability, register provider

---

## 11. CURRENT IMPLEMENTATION STATUS

### Fully Implemented ✅
- Core schemas and FCO definitions
- Immutable Plan domain and validation
- Append-only conversation history
- Workspace filesystem management
- Provider configuration system
- Model factory (OpenAI, Google, Anthropic)
- Executor registry and dispatcher
- Data Explorer deterministic operations
- Direct Task-to-Evidence admission pathway (MVP transitional)
- SQLModel persistence seams (SQLite verified)
- Planner REPL scaffold

### Partially Implemented 🔶
- Hypothesis Analyst (scaffold, stub graph)
- Graph Miner (read-only stub)
- PlannerOperation commit transaction

### Deferred ❌
- Human approval workflow
- Plan activation and active selection
- Task DAG runtime execution
- Scientific investigation protocol
- Protected evaluation
- Governance and Discovery admission
- Semantic graph query
- Restart-safe continuity
- Multi-session resume
- Validity transitions
- DVC data versioning

### MVP-v2 Definition of Done
- Complete scientific research loop
- Plan proposal and approval
- Execution and Evidence admission
- Hypothesis testing and evaluation
- Discovery admission
- Restart and grounded follow-up

---

## 12. KEY DESIGN DECISIONS

### Separation of Concerns
- Planner never acquires: scientific authorship, Evidence creation, persistence authority
- Specialists never communicate directly with human; only through Application
- Authority plane validates every state transition before admission
- Governance reviews only exact eligible proposals; cannot rewrite content

### Validity Preservation
- Immutability: FCOs frozen after creation
- Append-Only History: Never deleted, only superseded
- Lineage Tracking: Every artifact linked to source
- Eligibility Checks: Current-use status verified at retrieval

### Type Safety
- Pydantic Models: All state validated
- Protocol Enforcement: Specialist contracts via structural types
- Enum-Based Routing: Capabilities via StrEnum
- Configuration Validation: ProjectConfig validates provider existence

### Multi-Session Continuity
- Workspace-First: All state scoped to workspace
- Explicit Context: SessionFrame captures membership
- Durable Persistence: SQLite records all decisions
- Environment Isolation: Each workspace has .env

---

## 13. RECOMMENDED WIKI STRUCTURE

1. **Overview** - What is CogniEDA, main concepts
2. **Architecture** - System design, three planes, component responsibilities
3. **Authority & Governance** - Decision boundaries, approval workflow
4. **Execution Model** - Dispatch, capabilities, specialist contracts
5. **Data Model** - FCOs, schemas, persistence
6. **Configuration** - Workspace, providers, skills, MCP
7. **Runtime** - Bootstrap, REPL, message flow, commands
8. **Agent Specializations** - Planner, Data Explorer, Hypothesis Analyst, Graph Miner
9. **Workflows** - Planning, consultation, execution, admission
10. **Extension Points** - Custom agents, skills, providers, persistence
11. **API Reference** - Key classes, methods, schemas
12. **Development** - Setup, testing, debugging
13. **Status & Roadmap** - Current state, deferred work, MVP-v2


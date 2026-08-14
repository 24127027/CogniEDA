# CogniEDA Repository Comprehensive Inventory

**Generated:** 2026-08-14  
**Repository Context:** Python 3.12+ research-state infrastructure for analytical investigation

---

## 1. Main Purpose & High-Level Architecture

### Purpose
CogniEDA is **validity-preserving research-state infrastructure** for analytical investigation. It keeps research intent, data state, planning assumptions, scientific commitments, observations, claims, validity, provenance, and active context distinct and traceable across multi-session investigations.

### Architectural Priorities (in order)
1. **Conclusion validity and traceability** — claims remain connected to state/evidence
2. **Context type safety** — ineligible material excluded from protected reasoning
3. **Multi-session continuity** — safe resumption with governed state, not transcript replay
4. **Speed and convenience** — only after the first three are protected

### High-Level Operating Model
```
human intent
  -> governed planning (Planner)
  -> bounded specialist work (Data Explorer, Hypothesis Analyst, Graph Miner)
  -> authoritative admission (Application Authority)
  -> protected evaluation (Governance)
  -> governed outcome (Discovery/Non-Discovery)
  -> validity-aware continuity
```

### Three Cooperating Planes

| Plane | Components | Purpose |
|-------|-----------|---------|
| **Control** | Human, Planner | Intent, coordination, approval, routing, presentation |
| **Specialist** | Data Explorer, Hypothesis Analyst, Graph Miner | Role-specific bounded work without governance authority |
| **Authority** | Application Authority, Governance, Persistence | Validation, admission, lifecycle transitions, replay safety |

---

## 2. All Packages and Primary Responsibilities

### Top-Level Package Structure
```
src/cognieda/
├── agents/              # Specialist cognitive coordinators
├── application/         # Service layer and ports
├── cli/                 # Command-line entry points
├── execution/           # Task dispatch and capability routing
├── infrastructure/      # External integrations
├── runtime/             # Application bootstrap and session lifecycle
└── schemas/             # Pydantic domain models and validation
```

### `agents/` — Specialist Agents (4 + utilities)

#### 2.1 `agents/planner/`
- **Files:** `agent.py`, `context.py`, `dependencies.py`, `types.py`, `instruction/`
- **Responsibility:** Control-plane cognitive coordinator
- **Authority:** ✅ Objective coordination, Plan/Task proposals, routing, replanning | ❌ Scientific operationalization, Hypothesis authoring, Evidence creation
- **Key Classes:**
  - `Planner` — Human-facing coordinator, manages model agent lifecycle
  - `PlannerContext` — Readable research state for single invocation
  - `PlannerDeps` — Frozen dependencies (executor dispatcher)
  - `PlannerResult` — Semantic conclusions (Plan, response, continue, human_input_request)

#### 2.2 `agents/data_explorer/`
- **Files:** `agent.py`, `contracts.py`, `planning.py`, `__init__.py`, `tools/`
- **Responsibility:** Bounded data analysis and profiling
- **Authority:** ✅ Dataset inspection, observations, AnalysisFrame | ❌ Hypothesis definition, hypothesis evaluation, direct persistence
- **Key Classes:**
  - `DataExplorer` — Provider for data analysis/profiling capability requests
  - `DataExplorerResult` — Role-native results with provenance
  - `DataAnalysisPlan` — Contract for data work scope
  - `DataProfileCandidate` — Observation of dataset state

#### 2.3 `agents/hypothesis_analyst/`
- **Files:** `agent.py`, `contracts.py`, `deps.py`, `graph.py`, `state.py`
- **Responsibility:** Scientific investigation controller (scaffolding/deferred)
- **Authority:** ✅ Scientific feasibility, Hypothesis operationalization, protocol definition | ❌ Dataset direct access, governance self-approval
- **Status:** Donor wrapper; S0 does not register as runnable

#### 2.4 `agents/graph_miner/`
- **Files:** `agent.py`, `graph.py`, `state.py`
- **Responsibility:** Read-only knowledge graph analysis (deferred)
- **Authority:** ✅ Graph traversal, read-only queries | ❌ Mutations, dataset access, Evidence/Discovery creation
- **Status:** Stub; raises NotImplementedError at runtime

#### 2.5 `agents/utilities/`
- **Files:** `instruction.py`
- **Responsibility:** Instruction assembly for Planner

### `application/` — Service Layer & Contracts

#### 2.6 `application/ports/`
- **Files:** `llm.py`, `execution.py`, `__init__.py`
- **Key Types:**
  - `ModelConfig` — Provider selection and credentials
  - `ProviderType` — Literal["openai", "google", "anthropic"]
  - `AgentFactoryPort` — Protocol for agent creation
  - `ExecutorDispatcherPort` — Protocol for capability dispatch

#### 2.7 `application/services/`
- **Files:** `execution_admission.py`, `mvp_data_admission.py`, `planner_commit.py`, `plan_validation.py`, `transition_service.py`
- **Responsibility:** Admission workflows and state transitions

### `cli/` — Command-Line Entry Points

#### 2.8 CLI Components
- **`app.py`** — Installed command-line entrypoint with parser
- **`main.py`** — Async REPL scaffold
- **`renderer.py`** — UI output formatting
- **`mock_application.py`** — Standalone UI playground

### `execution/` — Dispatch & Capability Routing

#### 2.9 Execution Components
- **`capabilities.py`** — Finite capability enum (DATA_ANALYSIS, DATA_PROFILING, DATA_TRANSFORMATION, GRAPH_MINING, HYPOTHESIS_TESTING)
- **`contracts.py`** — Request/result transport schemas
- **`dispatcher.py`** — Capability request router
- **`registry.py`** — Provider registration and resolution

### `infrastructure/` — External Integrations & Services

#### 2.10 Infrastructure Layers

| Layer | Module | Purpose | Status |
|-------|--------|---------|--------|
| **LLM** | `llm/factory.py` | PydanticAI agent creation with model selection (OpenAI, Google, Anthropic) | Active |
| **Persistence** | `persistence/` | SQLite via SQLModel ORM | Verified on SQLite only |
| **Tooling** | `agent_tooling/` | Skill and MCP loader from TOML | Active |
| **MCP** | `mcp/` | Model Context Protocol server definitions | Config surface only |
| **Skills** | `skills/` | pydantic_ai_skills capability system | Framework only |
| **Datasets** | `datasets/` | Data loading and profiling | Active |
| **DVC** | `dvc/` | Data versioning integration | Placeholder |

### `runtime/` — Application Bootstrap & Session Lifecycle

#### 2.11 Runtime Components
- **`application.py`** — Main Application orchestrator with command handling
- **`bootstrap.py`** — Application factory
- **`workspace.py`** — Project root and configuration management
- **`conversation.py`** — Append-only message history
- **`messages.py`** — Message transport types
- **`planner_context.py`** — Planner input construction

---

## 3. All Agents (Data, Responsibilities, Authority Boundaries)

### Agent Authority Matrix

| Agent | Data Access | Scope | Authority | Cannot Do |
|-------|-------------|-------|-----------|-----------|
| **Planner** | SessionFrame, history | Intent→Plan | Objective, routing, replanning | Scientific operationalization, Evidence creation |
| **Data Explorer** | Datasets | Bounded analysis | Observations, profiling | Hypothesis definition, governance |
| **Hypothesis Analyst** | None (delegation) | Scientific protocols | Feasibility, methods, evaluation | Dataset direct access, persistence |
| **Graph Miner** | Read-only graphs | Knowledge traversal | Queries, metrics | Mutations, Evidence, governance |

---

## 4. Application Services & Ports

| Service | File | Responsibility |
|---------|------|-----------------|
| Execution Admission | `services/execution_admission.py` | Validate and admit execution results |
| Data Admission | `services/mvp_data_admission.py` | Admit DataProfiles under MVP constraints |
| Planner Commit | `services/planner_commit.py` | Atomic persistence of planner decisions |
| Plan Validation | `services/plan_validation.py` | Structural DAG and Task validation |
| Transition Service | `services/transition_service.py` | Lifecycle and validity state changes |

---

## 5. Infrastructure Layers

### Persistence Layer
- **Technology:** SQLite (SQLModel ORM)
- **Status:** Verified on SQLite only
- **Components:** `init_db.py`, `models.py`, `migrations.py`, `session.py`

### LLM Layer
- **Module:** `infrastructure/llm/factory.py`
- **Providers:** OpenAI, Google (Gemini), Anthropic
- **Creates:** PydanticAI agents with model selection and toolsets

### Agents Tooling Layer
- **Module:** `infrastructure/agent_tooling/`
- **Sources:** `agents.toml`, `skills.toml`, `mcp.toml`
- **Function:** Composes skills and MCP servers per worker

### MCP (Model Context Protocol) Layer
- **Config:** `config/mcp.toml` (examples only)
- **Status:** Configuration surface; not fully integrated

### Skills Layer
- **Config:** `config/skills.toml` (examples only)
- **Framework:** pydantic_ai_skills capability loading

### DVC (Data Versioning) Layer
- **Module:** `infrastructure/dvc/`
- **Status:** Placeholder; deferred beyond S0

### Datasets Layer
- **Module:** `infrastructure/datasets/`
- **Function:** Load and profile datasets

---

## 6. Runtime & CLI Entry Points

### Installation & Startup
```powershell
uv sync
uv tool install --editable .
copy .env.example .env
cognieda                    # Current directory as workspace
cognieda PATH               # Specified workspace path
```

### CLI Structure
- **Entrypoint:** `src/cognieda/cli/app.py::main(argv)`
- **Parser:** `--mode {real,mock}`, workspace path
- **REPL:** Async event loop in `cli/main.py::repl(app, renderer)`
- **Mock Mode:** `MockApplication` for UI development

### Workspace Initialization
```
workspace/
├── .cognieda/
│   ├── project.toml        (Provider config)
│   ├── agents.toml         (Worker tooling)
│   ├── skills.toml         (Skill locations)
│   ├── mcp.toml            (MCP servers)
│   ├── skills/             (Local skill files)
│   ├── state/              (Runtime state)
│   └── sessions/           (Session history)
├── data/                   (Datasets)
├── .env                    (Credentials)
└── AGENTS.md               (Planner instructions)
```

---

## 7. Schema & Domain Models

### First-Class Objects (FCOs) — 8 Canonical Types

1. **Objective** — Research intent and boundaries (`objective_id`, `text`)
2. **DataProfile** — Immutable snapshot of dataset state (`data_profile_id`, `row_count`, `column_count`, `columns`)
3. **Assumption** — Planning-only statement (`assumption_id`, `text`)
4. **Task** — Objective-scoped semantic work identity (`task_id`, `objective_id`, `kind`, `instruction`, `status`)
5. **Hypothesis** — Atomic test contract from terminal Task (`hypothesis_id`, `task_id`, `profile_id`, `statement`, `scope`, `validation_method`)
6. **Evidence** — Immutable observation tied to data state (`evidence_id`, `task_id`, `data_profile_id`, `content`, `provenance`)
7. **Discovery** — Evidence-bound admitted claim (`discovery_id`, `hypothesis_id`, `evidence_ids`, `claim`, `epistemic_status`, `scope`, `validity_basis`)
8. **SessionFrame** — Active context for one invocation

### Non-FCO Provenance Records
- **AnalysisFrame** — Provenance pointer for data view
- **ExecutionRun** — Provenance pointer for executor attempt
- **ExecutionOutbox** — Durable dispatch intent
- **DataProfileDatasetBinding** — Authoritative binding
- **Plan** — Immutable DAG over Tasks

### Schema Modules

| Module | Purpose |
|--------|---------|
| `artifacts.py` | FCO definitions |
| `common.py` | Base models, validators, common types |
| `enums.py` | All enumeration types |
| `plan.py` | Immutable Plan and PlanDependency |
| `provenance.py` | Non-FCO provenance records |
| `planner_operations.py` | Planner-facing operations |

---

## 8. Test Structure & Key Patterns

### Test Directory
```
tests/
├── agents/test_llm.py
├── architecture/
│   ├── test_documentation_ia.py
│   ├── test_import_hygiene.py
│   ├── test_layer_boundaries.py
│   └── test_workspace_ownership.py
├── cli/
│   ├── test_app.py
│   ├── test_main.py
│   ├── test_mock_application.py
│   └── test_renderer.py
├── execution/test_registry_dispatcher.py
├── runtime/
│   ├── test_bootstrap_config.py
│   ├── test_conversation.py
│   ├── test_planner_context.py
│   └── test_workspace.py
└── schemas/test_mvp_data_profile.py
```

### Verification Commands
```powershell
uv run pytest              # All tests
uv run ruff check .        # Linting
uv run mypy src/cognieda  # Type checking (strict mode)
```

---

## 9. Configuration Files & Purpose

| File | Location | Purpose | Status |
|------|----------|---------|--------|
| `pyproject.toml` | Root | Package metadata, dependencies | Active |
| `project.toml` | `.cognieda/` | Provider profiles | Per-workspace |
| `agents.toml` | `.cognieda/` | Worker tooling | Per-workspace |
| `skills.toml` | `.cognieda/` | Skill directories | Per-workspace |
| `mcp.toml` | `.cognieda/` | MCP servers | Per-workspace |
| `.env` | Workspace root | Credentials | Per-workspace |
| `.env.example` | Root | Environment template | Template |

### `.env.example` Variables
```
COGNIEDA_MODEL_PROVIDER=google
COGNIEDA_MODEL_NAME=gemini-3.5-flash
MODEL_API_KEY=<set-this>
MODEL_BASE_URL=<optional>
COGNIEDA_DB_URL=<optional>
COGNIEDA_DB_ECHO=false
```

---

## 10. Major Workflows & Data Flows

### 1. Application Initialization Flow
```
CLI app.py
  ↓ parse_args()
  ↓ bootstrap_application(workspace_path)
  ├─ _load_workspace_environment() [Load .env]
  ├─ Workspace.open() [Initialize directories]
  ├─ ProjectConfig.load() [Read project.toml]
  ├─ AgentFactory(workspace) [Load tooling]
  ├─ ExecutorRegistry.register_provider(DataExplorer, [capabilities])
  ├─ Planner(deps, agent_factory, model_config, instruction)
  └─ Application(workspace, planner, dispatcher, agent_factory)
  ↓ repl(app, renderer)
```

### 2. Message Processing Flow
```
User input
  ↓ app.submit_message(text)
  ├─ IF /command: _handle_command()
  │   ├─ /skill add|rm|list|use|drop
  │   ├─ /provider use|list|key|model
  │   └─ /reload
  │
  └─ ELSE: planner_agent.run(message, context)
     ├─ build_planner_context(session_frame, history)
     ├─ LLM inference (PydanticAI)
     ├─ Tool/skill execution
     ├─ ConversationHistory.add_turn()
     └─ Message(ASSISTANT, _present_planner_result())
```

### 3. Data Explorer Capability Flow
```
ExecutorDispatcher.dispatch(ExecutionRequest)
  ├─ request.capability ∈ {DATA_ANALYSIS, DATA_PROFILING, DATA_TRANSFORMATION}
  ↓ registry.resolve() → DataExplorer
  ↓ DataExplorer.run(request)
  ├─ Load dataset
  ├─ Execute DataAnalysisPlan
  └─ Return DataExplorerResult
```

### 4. Research State Lifecycle
```
Objective (ACTIVE)
  ├─ Plan (proposed)
  │  └─ Tasks: [DATA, DATA, SCIENTIFIC]
  │
  ├─ DATA Tasks execute
  │  └─ Observations generated
  │
  ├─ SCIENTIFIC Task
  │  ├─ Hypothesis Analyst: feasibility check
  │  ├─ IF feasible → Hypothesis + protocol
  │  ├─ Analysis execution
  │  ├─ Evidence admission
  │  ├─ Protected evaluation
  │  ├─ DiscoveryProposal
  │  ├─ Governance decision
  │  └─ Discovery admitted (CONFIRMED|INCONCLUSIVE|CONTRADICTED)
  │
  └─ Validity state updated
     ├─ Historical truth preserved
     ├─ Current-use eligibility changed (if data/method changes)
     └─ Flagged for review if needed
```

### 5. Multi-Session Continuity
```
Session 1:
  ├─ Workspace created
  ├─ Objective + Plan established
  ├─ DATA tasks execute
  └─ State persisted to SQLite

Session 2 (Resume):
  ├─ Workspace.open() loads existing `.cognieda/`
  ├─ Persistence layer retrieves:
  │  ├─ Last Objective
  │  ├─ Last successful Plan
  │  ├─ Task status
  │  ├─ Evidence with validity flags
  │  └─ Discovery with supersession info
  ├─ SessionFrame reconstructed with eligible context
  └─ Planner can see validity changes and proceed safely
```

---

## 11. Current Implementation Status (MVP-S0)

### What Is Implemented ✅

- **Core Infrastructure:** Pydantic schemas for all 8 FCOs + provenance, SQLite persistence, Workspace initialization
- **Planner & Runtime:** REPL scaffold, message routing, Conversation history, Plan DAG with validation
- **Data Explorer:** Dataset loading, profiling, bounded data analysis planning
- **Execution:** ExecutorRegistry, dispatcher, capability routing, result validation
- **Testing:** Pytest, mypy strict, ruff, architecture boundary tests

### What Is Deferred ❌ (Beyond MVP-S0)

- **Hypothesis Analyst:** Scientific feasibility, protocol definition, protected evaluation
- **Graph Miner:** Runtime implementation, knowledge graph traversal
- **Advanced Features:** DVC versioning, full MCP composition, Product CLI (scaffold only), Human approval workflows, Plan activation
- **Persistence:** Non-SQLite support, snapshot versioning, replay mechanisms, multi-workspace federation

### Known Limitations

1. **Database:** Only SQLite verified
2. **Planner Execution:** Stubs for specialist dispatch; not fully orchestrated
3. **Scientific Loop:** Hypothesis Analyst and Graph Miner are scaffolds
4. **Governance:** No approval workflow or review queue
5. **Skills & MCP:** Configuration present; integration incomplete
6. **Product CLI:** Current entry point is development REPL, not supported product

---

## 12. Architecture Decision Records (Stable)

| Decision | Consequence |
|----------|-------------|
| **Authority Separation** | No participant acquires all authority; model output remains proposal until admitted |
| **FCO Definition** | Exactly 8 canonical FCOs; clear state classification; no semantic creep |
| **Research State Layers** | Intent, planning, data, scientific, observations, claims are separate with own lifecycle |
| **Validity as Property** | Historical truth ≠ current-use eligibility; old findings preserved and visible |
| **Immutability** | Evidence and Discovery immutable; changes create successors; audit trail guaranteed |

---

## Summary: Architectural Coherence

CogniEDA achieves coherence through **strict authority separation** and **explicit state layering**:

1. **Control** (Human, Planner) proposes intent and plans
2. **Specialists** (Data Explorer, Hypothesis Analyst, Graph Miner) execute bounded work
3. **Authority** (Application, Governance) validates, admits, and preserves state
4. **Validity** distinguishes historical truth from current-use eligibility

This allows:
- Long-running investigations without losing intent or evidence
- Safe multi-session resumption with governed state, not transcript replay
- Trustworthy findings tied to data state, method, and approval chain
- Restraint — incomplete work remains exactly that, not promoted to conclusions

**Implementation Status:** MVP-S0 with foundational schemas, persistence, and Planner REPL. Scientific investigation loop (Hypothesis Analyst) and graph analysis (Graph Miner) are deferred scaffolds. Product CLI support is beyond scope.

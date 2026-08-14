# CogniEDA Developer Quick Reference

**Purpose:** Fast lookup for developers navigating CogniEDA codebase

---

## Quick Navigation

### Where to Find Things

| Need | Location | Key Files |
|------|----------|-----------|
| **Start here** | `docs/index.md` | Canonical documentation index |
| **What is it?** | `docs/what-is-cognieda.md` | Conceptual overview |
| **Architecture** | `docs/architecture/system-overview.md` | System boundaries and flows |
| **Current status** | `docs/status/current-state.md` | What's implemented, what's deferred |
| **Authority rules** | `docs/architecture/authority-boundaries.md` | Who owns what |
| **Planner** | `src/cognieda/agents/planner/` | Cognitive coordinator |
| **Data Explorer** | `src/cognieda/agents/data_explorer/` | Data analysis provider |
| **Schemas** | `src/cognieda/schemas/` | All domain models |
| **Persistence** | `src/cognieda/infrastructure/persistence/` | SQLite ORM models |
| **Tests** | `tests/` | Architecture, schema, integration tests |
| **CLI** | `src/cognieda/cli/app.py` | Entry point and argument parsing |

---

## Installation & Setup

```powershell
# Clone and environment setup
git clone <repo>
cd CogniEDA
uv sync                           # Install dev dependencies
uv tool install --editable .      # Editable CLI install

# Configuration
copy .env.example .env
# Edit .env: set MODEL_API_KEY and COGNIEDA_MODEL_PROVIDER

# Run
cognieda                          # Current dir as workspace
cognieda /path/to/workspace       # Specific workspace
python -m cognieda                # Via module

# Verify
uv run pytest                     # All tests
uv run ruff check .               # Linting
uv run mypy src/cognieda         # Type checking (strict)
```

---

## Key Classes & Their Roles

### Application Entry Point
```python
# src/cognieda/runtime/application.py
class Application:
    workspace: Workspace              # Root and config
    planner_agent: Planner           # Cognitive coordinator
    dispatcher: ExecutorDispatcher   # Routes to specialists
    agent_factory: AgentFactoryPort # Creates agents
    session_frame: SessionFrame       # Active context
    conversation_history: ConversationHistory

    async def submit_message(message: str) -> Message
    async def _handle_command(command: str) -> Message
    async def _reload_runtime(...)
```

### Bootstrap
```python
# src/cognieda/runtime/bootstrap.py
def bootstrap_application(workspace_path: Path) -> Application:
    # 1. Load workspace environment (.env)
    # 2. Open workspace (create dirs if needed)
    # 3. Resolve model config (provider + credentials)
    # 4. Create agent factory
    # 5. Register Data Explorer executor
    # 6. Create Planner
    # 7. Return Application
```

### Planner
```python
# src/cognieda/agents/planner/agent.py
class Planner:
    deps: PlannerDeps              # Contains dispatcher
    _agent_factory: AgentFactoryPort
    _model_config: ModelConfig | None
    _agent: Agent[PlannerDeps] | None

    async def run(message: str, context: PlannerContext) -> PlannerOutput
    async def reload(...)
```

### Workspace
```python
# src/cognieda/runtime/workspace.py
class Workspace:
    root: Path
    project_config: ProjectConfig

    @classmethod
    def open(root: Path) -> Workspace
    @classmethod
    def initialize(root: Path)
    
    # Directories
    @property
    def cognieda_dir: Path              # .cognieda/
    @property
    def data_dir: Path                  # data/
    @property
    def state_dir: Path                 # .cognieda/state/
    @property
    def session_dir: Path               # .cognieda/sessions/

    # Config management
    load_planner_instruction() -> str
    load_agents_config() -> dict
    load_skills_config() -> dict
    add_skill(name, directory)
    remove_skill(name)
```

### Execution Dispatch
```python
# src/cognieda/execution/dispatcher.py
class ExecutorDispatcher:
    async def dispatch(request: ExecutionRequest) -> ExecutionResult

# src/cognieda/execution/registry.py
class ExecutorRegistry:
    def register_provider(provider_fn, capabilities: tuple[Capability, ...])
    def resolve(capability: Capability) -> ExecutorProvider
```

### Data Explorer
```python
# src/cognieda/agents/data_explorer/agent.py
class DataExplorer:
    async def run(request: ExecutionRequest) -> ExecutionResult
    # Returns: DataExplorerResult with status, task_id, work_id, content
```

### Persistence
```python
# src/cognieda/infrastructure/persistence/session.py
# SQLite session via SQLModel

# Models in models.py:
# - Objective, DataProfile, Task, Hypothesis, Evidence, Discovery, SessionFrame (FCOs)
# - AnalysisFrame, ExecutionRun, ExecutionOutbox, DataProfileDatasetBinding (provenance)
# - Plan, PlanDependency (structural)
```

---

## Key Data Types

### Research State FCOs

```python
# src/cognieda/schemas/artifacts.py

class Objective(ImmutableCogniEDABaseModel):
    objective_id: UUID
    text: NonEmptyStr                  # Research intent

class DataProfile(ImmutableCogniEDABaseModel):
    data_profile_id: UUID
    row_count: NonNegativeInt
    column_count: NonNegativeInt
    columns: tuple[ColumnProfile, ...]

class Assumption(ImmutableCogniEDABaseModel):
    assumption_id: UUID
    text: NonEmptyStr                  # Planning-only, never evidence

class Task(ImmutableCogniEDABaseModel):
    task_id: UUID
    objective_id: UUID
    kind: TaskKind                     # DATA, SCIENTIFIC, GRAPH
    instruction: NonEmptyStr
    status: TaskStatus                 # PENDING, ACTIVE, COMPLETED, FAILED

class Hypothesis(CogniEDABaseModel):
    hypothesis_id: UUID
    task_id: UUID
    profile_id: UUID
    statement: NonEmptyStr
    scope: NonEmptyStr
    validation_method: NonEmptyStr
    status: HypothesisStatus           # PROPOSED, ACTIVE, COMPLETED

class Evidence(ImmutableCogniEDABaseModel):
    evidence_id: UUID
    task_id: UUID
    data_profile_id: UUID
    content: dict[str, JsonValue]      # Immutable JSON
    provenance: EvidenceProvenance

class Discovery(ImmutableCogniEDABaseModel):
    discovery_id: UUID
    hypothesis_id: UUID
    evidence_ids: list[UUID]
    claim: DiscoveryClaim
    epistemic_status: DiscoveryEpistemicStatus  # CONFIRMED, INCONCLUSIVE, CONTRADICTED
    scope: NonEmptyStr
    validity_basis: ValidityBasis
    lifecycle_state: DiscoveryLifecycleState    # ACTIVE, SUPERSEDED, INVALIDATED

class SessionFrame(ImmutableCogniEDABaseModel):
    # Active context for one invocation
```

### Execution Contracts

```python
# src/cognieda/execution/contracts.py

class ExecutionRequest(BaseModel):
    capability: Capability             # DATA_ANALYSIS, DATA_PROFILING, etc.
    input: ExecutorInput               # Contains Task
    context: ExecutorContext = {}      # dataset_path, data_profile_id

class ExecutionResult(BaseModel):
    source_role: str                   # "data_explorer", etc.
    task_id: UUID
    work_id: str                       # Unique work identifier
    status: ExecutionStatus            # SUCCEEDED, BLOCKED, FAILED
    limitations: list[str] = []
    failure: ExecutionFailure | None   # Only if not SUCCEEDED
```

### Planner Results

```python
# src/cognieda/agents/planner/types.py

class PlannerResult(BaseModel):
    plan: Plan | None = None           # Proposed DAG
    tasks: tuple[Task, ...] = ()       # Terminal tasks
    response: str | None = None        # Natural language response
    human_input_request: str | None = None
    continue_execution: bool = False

class PlannerOutput(BaseModel):
    result: PlannerResult
    messages: tuple[ModelMessage, ...] = ()
    error: PlannerControlledError | None = None
```

### Plan (Structural)

```python
# src/cognieda/schemas/plan.py

class Plan(ImmutableCogniEDABaseModel):
    plan_id: UUID
    objective: Objective               # Exact Objective reference
    assumptions: tuple[Assumption, ...] = ()
    task_ids: tuple[UUID, ...] = ()    # Member Task IDs
    dependencies: tuple[PlanDependency, ...] = ()
    # Canonical ordering enforced by validators

class PlanDependency(ImmutableCogniEDABaseModel):
    prerequisite_task_id: UUID
    dependent_task_id: UUID
```

### Message History

```python
# src/cognieda/runtime/conversation.py

class ConversationTurn(CogniEDABaseModel):
    turn_id: UUID
    messages: tuple[ModelMessage, ...]  # Native PydanticAI messages

class ConversationHistory(CogniEDABaseModel):
    turns: tuple[ConversationTurn, ...] = ()

    def add_turn(messages: Iterable[ModelMessage]) -> ConversationHistory
    def model_messages() -> list[ModelMessage]  # Flattened for agent
```

---

## Common Workflows

### 1. Add a Skill at Runtime

```python
# Via CLI command
/skill add memory_management ./skills/memory

# Behind the scenes:
# 1. workspace.add_skill(name, directory)
# 2. workspace.save_skills_config()
# 3. await app._reload_runtime(reload_tooling=True, recreate_agent=True)
# 4. agent_factory.reload_tooling()
# 5. planner_agent.reload(recreate_agent=True)
```

### 2. Switch LLM Provider

```python
# Via CLI command
/provider use openai
/provider key openai

# Behind the scenes:
# 1. workspace.use_provider(profile)
# 2. workspace.set_provider_api_key(profile, api_key)
# 3. await app._reload_runtime(recreate_agent=True)
# 4. Planner agent recreated with new model config
```

### 3. Dispatch Capability Request

```python
from cognieda.execution import Capability, ExecutionRequest, ExecutorInput

# Create request
request = ExecutionRequest(
    capability=Capability.DATA_ANALYSIS,
    input=ExecutorInput(task=my_task),
    context=ExecutorContext(dataset_path="./data/raw.csv")
)

# Dispatch
result = await dispatcher.dispatch(request)

# Check result
if result.status == ExecutionStatus.SUCCEEDED:
    # Process result
    pass
else:
    # Handle failure
    print(result.failure.message)
```

### 4. Create Planner Context

```python
from cognieda.runtime.planner_context import build_planner_context

context = build_planner_context(
    session_frame=app.session_frame,
    conversation_history=app.conversation_history
)

# Context contains:
# - active_plan: Last valid Plan
# - objective: Current Objective
# - assumptions: All Assumptions
# - tasks: All Tasks
# - evidences: Admitted Evidence
# - discoveries: Admitted Discoveries
# - data_profile: Active DataProfile
# - conversation_history: Full turn history
```

### 5. Admit Evidence

```python
from cognieda.schemas.artifacts import Evidence
from cognieda.schemas.provenance import DataProfileDatasetBinding

# After executor produces observation
evidence = Evidence(
    task_id=task.task_id,
    data_profile_id=profile.data_profile_id,
    content={
        "correlation": 0.42,
        "p_value": 0.001,
        "n": 1000
    },
    provenance=EvidenceProvenance(
        data_profile_id=profile.data_profile_id,
        method="pearson_correlation",
        analysis_frame_id=frame.analysis_frame_id
    )
)

# Validate and persist
# (Application authority handles admission via services layer)
```

---

## Testing Patterns

### Architecture Tests
```python
# tests/architecture/test_layer_boundaries.py
# Enforce import hygiene and layer separation
# Example: agents/ cannot import from application/

# tests/architecture/test_workspace_ownership.py
# Verify workspace directory structure

# tests/architecture/test_documentation_ia.py
# Verify docs referenced in code are present
```

### Schema Tests
```python
# tests/schemas/test_mvp_data_profile.py
# Test immutability, validation, canonical ordering

def test_plan_rejects_duplicate_task_ids():
    with pytest.raises(ValueError):
        Plan(objective=obj, task_ids=(id1, id1))
```

### Runtime Tests
```python
# tests/runtime/test_workspace.py
# Test workspace initialization, config loading/saving

# tests/runtime/test_bootstrap_config.py
# Test application initialization

# tests/runtime/test_conversation.py
# Test message history append-only semantics
```

### Execution Tests
```python
# tests/execution/test_registry_dispatcher.py
# Test capability routing and provider resolution
```

---

## Configuration Deep Dive

### `.env` (Per Workspace)
```bash
# LLM provider configuration
COGNIEDA_MODEL_PROVIDER=google              # google, openai, anthropic
COGNIEDA_MODEL_NAME=gemini-3.5-flash
MODEL_API_KEY=<your-api-key>
MODEL_BASE_URL=                             # Optional: custom endpoint

# Database configuration
COGNIEDA_DB_URL=                            # SQLite path (default: package-local)
COGNIEDA_DB_ECHO=false                      # Log SQL statements
```

### `.cognieda/project.toml` (Per Workspace)
```toml
default_provider = "google"

[providers.google]
type = "google"
model = "gemini-2.0-flash"
api_key_env = "GOOGLE_API_KEY"
base_url = ""

[providers.openai]
type = "openai"
model = "gpt-4o"
api_key_env = "OPENAI_API_KEY"
base_url = ""

[providers.anthropic]
type = "anthropic"
model = "claude-3-5-sonnet"
api_key_env = "ANTHROPIC_API_KEY"
```

### `.cognieda/agents.toml` (Per Workspace)
```toml
# Example (currently all commented)
# [planner]
# skills = ["memory_management", "task_planning"]
# mcp = ["filesystem"]
```

### `.cognieda/skills.toml` (Per Workspace)
```toml
# Example (currently all commented)
# [memory_management]
# id = "memory_management"
# directories = ["./skills/memory"]
# description = "Manage session frames and assumptions"
```

---

## Key Enumerations

### TaskKind
```python
class TaskKind(StrEnum):
    DATA = "data"              # Data profiling/analysis
    SCIENTIFIC = "scientific"  # Hypothesis-driven investigation
    GRAPH = "graph"            # Knowledge graph queries
```

### TaskStatus
```python
class TaskStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
```

### DiscoveryEpistemicStatus
```python
class DiscoveryEpistemicStatus(StrEnum):
    CONFIRMED = "confirmed"                        # Hypothesis supported
    VALUABLE_INCONCLUSIVE = "valuable_inconclusive"
    CONTRADICTED = "contradicted"                  # Hypothesis rejected
    NOT_TESTABLE = "not_testable"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
```

### ExecutionStatus
```python
class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"
```

### Capability
```python
class Capability(StrEnum):
    DATA_ANALYSIS = "data_analysis"
    DATA_PROFILING = "data_profiling"
    DATA_TRANSFORMATION = "data_transformation"
    GRAPH_MINING = "graph_mining"
    HYPOTHESIS_TESTING = "hypothesis_testing"
```

---

## Debugging Tips

### Enable SQL Logging
```bash
COGNIEDA_DB_ECHO=true cognieda
```

### Check Workspace State
```bash
cd <workspace>
cat .cognieda/project.toml      # Provider config
cat .env                        # Credentials
ls -la .cognieda/               # State and sessions
```

### View CLI Help
```bash
cognieda --help
```

### Test Locally (Mock Mode)
```bash
cognieda --mode mock
# Launches UI playground without runtime bootstrap
```

### Inspect Agent Tooling
```python
# In interactive Python
from cognieda.infrastructure.agent_tooling import AgentTooling
from cognieda.runtime.workspace import Workspace

ws = Workspace.open(".")
tooling = AgentTooling.load(ws)

# Inspect worker tooling
tooling.toolsets_for("planner")
tooling.skills_for("data_explorer")
```

---

## Authority Reminders

| Boundary | Rule |
|----------|------|
| **Planner** | Proposes plans; never writes Evidence, Discovery, or scientific protocols |
| **Data Explorer** | Accesses datasets exclusively; returns observations only (not interpretations) |
| **Hypothesis Analyst** | Owns scientific protocols; never accesses datasets directly or persists state |
| **Graph Miner** | Read-only queries; cannot mutate state or access datasets |
| **Application Authority** | Validates contracts, admits state, ensures replay safety |
| **Governance** | Reviews proposals; cannot rewrite admitted content |

---

## Common Mistakes to Avoid

❌ **Don't:**
- Create an Assumption and treat it as Evidence
- Have Data Explorer author a Hypothesis
- Import from a lower layer into a higher layer (execution can't import from infrastructure)
- Admit state without validation
- Mutate Evidence or Discovery after creation
- Create a Discovery without Evidence linkage

✅ **Do:**
- Keep planning assumptions separate from scientific Evidence
- Route all specialist work through Application Authority
- Respect layer boundaries (cli → runtime → application → infrastructure)
- Validate all external input before persistence
- Use immutable FCO types for durable state
- Link all Discoveries to admitted Evidence

---

## Further Reading

| Topic | Location |
|-------|----------|
| Full conceptual model | `docs/what-is-cognieda.md` |
| Failure modes motivating design | `docs/problem-and-thesis.md` |
| Research state layers | `docs/concepts/research-state/index.md` |
| Authority separation | `docs/architecture/authority-boundaries.md` |
| Scientific lifecycle | `docs/concepts/scientific-lifecycle/index.md` |
| Validity and state changes | `docs/concepts/validity/index.md` |
| Context and continuity | `docs/concepts/context/index.md` |
| Current implementation status | `docs/status/current-state.md` |

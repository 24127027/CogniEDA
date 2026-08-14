# CogniEDA Complete Reference Guide

Comprehensive API, schema, and workflow documentation for CogniEDA development and integration.

---

## Part 1: CLI and Entrypoints

### Command: cognieda

Launch CogniEDA REPL with real or mock application.

```bash
cognieda [OPTIONS] [PATH]

Options:
  --mode {real,mock}    Run mode (default: real)
  PATH                  Workspace root (default: current directory)

Examples:
  cognieda                    # Launch with current directory
  cognieda /path/to/project   # Launch with specific workspace
  cognieda --mode mock        # Launch mock UI playground
```

### Entrypoint Flow

1. **Parse arguments** (app.py:parse_args)
2. **Choose mode**:
   - `--mode mock`: Return MockApplication
   - `--mode real`: Call bootstrap_application()
3. **Bootstrap application** (bootstrap.py:bootstrap_application)
4. **Launch REPL** (main.py:repl)

---

## Part 2: REPL Commands

### Skill Management

#### /skill add NAME DIRECTORY

Add a new skill from directory.

```
/skill add my_skill ./skills/my_skill
```

**Effect**:
- Update skills.toml
- Reload tooling
- Recreate agents

#### /skill rm NAME

Remove a skill.

```
/skill rm my_skill
```

#### /skill list

List all registered skills.

```
/skill list
```

**Output**:
```
my_skill: ./skills/my_skill
another_skill: ./skills/another
```

#### /skill use WORKER SKILL

Assign skill to worker.

```
/skill use planner my_skill
```

**Workers**: planner, data_explorer, hypothesis_analyst, graph_miner

#### /skill drop WORKER SKILL

Remove skill from worker.

```
/skill drop planner my_skill
```

### Provider Management

#### /provider list

List all configured providers.

```
/provider list
```

**Output**:
```
google
openai
anthropic
```

#### /provider (current status)

Show current provider and configuration.

```
/provider
```

**Output**:
```
Current provider : google
Model            : gemini-2.5-flash
API key          : yes
```

#### /provider use PROFILE

Switch to different provider.

```
/provider use openai
```

**Effect**:
- Update project.toml
- Resolve new model config
- Recreate Planner agent

#### /provider model PROFILE MODEL

Change model for provider.

```
/provider model openai gpt-4o
```

#### /provider key PROFILE

Set API key for provider.

```
/provider key openai
```

**Prompts**: `openai API key: `

**Effect**:
- Store in workspace .env
- Update os.environ
- Recreate agent

### System Commands

#### /reload

Reload Planner instructions from AGENTS.md.

```
/reload
```

**Effect**:
- Load workspace/AGENTS.md
- Recompile Planner system prompt
- Recreate agent with new instructions

#### exit, quit

Exit REPL.

```
exit
quit
```

---

## Part 3: Core Classes and Methods

### Application

**Location**: `src/cognieda/runtime/application.py`

```python
class Application:
    def __init__(
        self,
        workspace: Workspace,
        planner_agent: Planner,
        dispatcher: ExecutorDispatcher,
        agent_factory: AgentFactoryPort,
    ) -> None:
        self.workspace = workspace
        self.agent_factory = agent_factory
        self.planner_agent = planner_agent
        self.dispatcher = dispatcher
        self.session_frame = SessionFrame()
        self.conversation_history = ConversationHistory()

    async def submit_message(self, message: str) -> Message:
        """Process user message through Planner."""
        # Returns Message with type, role, content

    async def _reload_runtime(
        self,
        *,
        reload_tooling: bool = False,
        reload_instruction: bool = False,
        recreate_agent: bool = False,
    ) -> None:
        """Reload runtime components without restart."""
```

### Workspace

**Location**: `src/cognieda/runtime/workspace.py`

```python
class Workspace:
    root: Path
    project_config: ProjectConfig

    @classmethod
    def open(cls, root: Path) -> "Workspace":
        """Open existing workspace or initialize new."""

    @classmethod
    def initialize(cls, root: Path) -> None:
        """Create directory structure and default configs."""

    @property
    def cognieda_dir(self) -> Path:
        """~/.cognieda"""

    @property
    def data_dir(self) -> Path:
        """~/data"""

    @property
    def state_dir(self) -> Path:
        """~/.cognieda/state"""

    @property
    def session_dir(self) -> Path:
        """~/.cognieda/sessions"""

    def load_agents_config(self) -> dict:
        """Load agents.toml"""

    def load_skills_config(self) -> dict:
        """Load skills.toml"""

    def add_skill(self, name: str, directory: str) -> None:
        """Register skill directory"""

    def remove_skill(self, name: str) -> None:
        """Unregister skill"""

    def add_worker_skill(self, worker: str, skill: str) -> None:
        """Assign skill to worker"""

    def remove_worker_skill(self, worker: str, skill: str) -> None:
        """Unassign skill from worker"""

    def use_provider(self, profile: str) -> None:
        """Switch default provider"""

    def set_provider_model(self, profile: str, model: str) -> None:
        """Change model for provider"""

    def set_provider_api_key(self, profile: str, api_key: str) -> None:
        """Store API key in .env"""

    def load_agent_instruction(self) -> str:
        """Load AGENTS.md"""
```

### Planner

**Location**: `src/cognieda/agents/planner/agent.py`

```python
class Planner:
    def __init__(
        self,
        deps: PlannerDeps,
        *,
        agent_factory: AgentFactoryPort,
        model_config: ModelConfig | None,
        agent_instruction: str | None = None,
    ) -> None:
        self.deps = deps
        self._agent_factory = agent_factory
        self._model_config = model_config
        self._agent_instruction = agent_instruction

    async def reload(
        self,
        *,
        model_config: ModelConfig | None = None,
        agent_instruction: str | None = None,
        recreate_agent: bool = False,
    ) -> None:
        """Reload Planner configuration."""

    async def run(
        self,
        request: str,
        *,
        context: PlannerContext,
    ) -> PlannerOutput:
        """Invoke Planner for one request."""
        # Returns:
        # {
        #   messages: tuple[ModelMessage, ...],
        #   result: PlannerResult
        # }
```

### ExecutorDispatcher

**Location**: `src/cognieda/execution/dispatcher.py`

```python
class ExecutorDispatcher:
    def __init__(self, registry: ExecutorRegistry) -> None:
        self._registry = registry

    async def dispatch(self, request: ExecutionRequest) -> ExecutionResult:
        """Route capability request to provider."""
        # Resolves capability, dispatches to provider, handles errors
        # Returns ExecutionResult with status and failure info
```

### ExecutorRegistry

**Location**: `src/cognieda/execution/registry.py`

```python
class ExecutorRegistry:
    def __init__(self) -> None:
        self._providers: dict[Capability, ProviderFactory] = {}
        self._instances: dict[ProviderFactory, ExecutorProvider] = {}

    def register_provider(
        self,
        provider_factory: ProviderFactory,
        *,
        capabilities: Iterable[Capability],
    ) -> None:
        """Register provider with capabilities."""
        # Validates: callable factory, non-empty capabilities, no duplicates

    def resolve(self, capability: Capability) -> ExecutorProvider:
        """Get provider instance for capability."""
        # Lazy instantiation and caching

    def list_capabilities(self) -> tuple[Capability, ...]:
        """List all registered capabilities."""
```

### DataExplorer

**Location**: `src/cognieda/agents/data_explorer/agent.py`

```python
class DataExplorer:
    def __init__(
        self,
        *,
        config: ModelConfig | None = None,
        agent_factory: AgentFactoryPort | None = None,
        analysis_planner: DataAnalysisPlannerPort | None = None,
    ) -> None:
        self.config = config
        self.agent_factory = agent_factory
        self.analysis_planner = analysis_planner

    async def run(self, request: ExecutionRequest) -> ExecutionResult:
        """Execute data analysis or profiling."""
        # Validates request.capability in DATA_* set
        # Loads dataset, analyzes, returns ExecutionResult
```

---

## Part 4: Schema Reference

### Enums

#### Capability

```python
class Capability(StrEnum):
    DATA_ANALYSIS = "data_analysis"
    DATA_PROFILING = "data_profiling"
    DATA_TRANSFORMATION = "data_transformation"
    HYPOTHESIS_TESTING = "hypothesis_testing"
    GRAPH_MINING = "graph_mining"
```

#### TaskKind

```python
class TaskKind(StrEnum):
    DATA = "data"
    SCIENTIFIC = "scientific"
    GRAPH = "graph"
```

#### TaskStatus

```python
class TaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

#### ExecutionStatus

```python
class ExecutionStatus(StrEnum):
    SUCCEEDED = "succeeded"
    BLOCKED = "blocked"
    FAILED = "failed"
```

#### PlannerOperationType

```python
class PlannerOperationType(StrEnum):
    CREATE_OBJECTIVE_REVISION = "create_objective_revision"
    UPDATE_OBJECTIVE = "update_objective"
    CREATE_ASSUMPTION = "create_assumption"
    UPDATE_ASSUMPTION_STATE = "update_assumption_state"
    CREATE_HYPOTHESIS = "create_hypothesis"
    CREATE_EXECUTION_RUN = "create_execution_run"
    CREATE_EXECUTION_OUTBOX = "create_execution_outbox"
    CREATE_EVIDENCE = "create_evidence"
    CREATE_DISCOVERY = "create_discovery"
    UPDATE_SESSION_FRAME = "update_session_frame"
    FLAG_OBJECT = "flag_object"
```

### Core Models

#### Objective

```python
class Objective(ImmutableCogniEDABaseModel):
    objective_id: UUID = Field(default_factory=uuid4)
    text: NonEmptyStr
```

#### DataProfile

```python
class DataProfile(ImmutableCogniEDABaseModel):
    data_profile_id: UUID = Field(default_factory=uuid4)
    row_count: NonNegativeInt
    column_count: NonNegativeInt
    columns: tuple[ColumnProfile, ...]
```

#### Assumption

```python
class Assumption(ImmutableCogniEDABaseModel):
    assumption_id: UUID = Field(default_factory=uuid4)
    text: NonEmptyStr
```

#### Task

```python
class Task(ImmutableCogniEDABaseModel):
    task_id: UUID = Field(default_factory=uuid4)
    objective_id: UUID
    kind: TaskKind
    instruction: NonEmptyStr
    status: TaskStatus = TaskStatus.PENDING
```

#### Plan

```python
class Plan(ImmutableCogniEDABaseModel):
    plan_id: UUID = Field(default_factory=uuid4)
    objective: Objective
    assumptions: tuple[Assumption, ...] = ()
    task_ids: tuple[UUID, ...] = ()
    dependencies: tuple[PlanDependency, ...] = ()
```

#### PlanDependency

```python
class PlanDependency(ImmutableCogniEDABaseModel):
    prerequisite_task_id: UUID
    dependent_task_id: UUID
```

#### PlannerResult

```python
class PlannerResult(BaseModel):
    plan: Plan | None = None
    tasks: tuple[Task, ...] = ()
    response: str | None = Field(default=None, min_length=1)
    human_input_request: str | None = Field(default=None, min_length=1)
    continue_execution: bool = False
```

#### PlannerOutput

```python
@dataclass
class PlannerOutput:
    messages: tuple[ModelMessage, ...]
    result: PlannerResult
```

#### ExecutionRequest

```python
class ExecutionRequest(BaseModel):
    capability: Capability
    input: ExecutorInput
        task: Task
    context: ExecutorContext = Field(default_factory=ExecutorContext)
        dataset_path: str | None = None
        data_profile_id: UUID | None = None
```

#### ExecutionResult

```python
class ExecutionResult(BaseModel):
    source_role: str = Field(min_length=1)
    task_id: UUID
    work_id: str = Field(min_length=1)
    status: ExecutionStatus
    limitations: list[str] = Field(default_factory=list)
    failure: ExecutionFailure | None = None
```

#### ExecutionFailure

```python
class ExecutionFailure(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
```

#### Message

```python
class Message(BaseModel):
    type: MessageType
    role: MessageRole
    content: str
```

#### ModelConfig

```python
class ModelConfig(BaseModel):
    provider: ProviderType  # "openai" | "google" | "anthropic"
    model_name: str = ""
    base_url: str = ""
    api_key: str = ""
```

---

## Part 5: Workflow Patterns

### Workflow 1: Initialize and Launch

```python
from cognieda.runtime import bootstrap_application
from pathlib import Path

# Bootstrap entire application
workspace_path = Path("/path/to/workspace")
app = bootstrap_application(workspace_path)

# Launch REPL
from cognieda.cli.renderer import Renderer
import asyncio

renderer = Renderer()
asyncio.run(repl(app, renderer))
```

### Workflow 2: Add Custom Skill

```python
# 1. Create skill implementation (pydantic_ai_skills)
# 2. Place in workspace/skills/my_skill/

# 3. Register via REPL
/skill add my_skill ./skills/my_skill

# 4. Assign to worker
/skill use planner my_skill

# 5. Verify
/skill list
```

### Workflow 3: Switch Model Provider

```python
# 1. Ensure API key is available
export OPENAI_API_KEY="sk-..."

# 2. Switch provider via REPL
/provider use openai

# 3. Verify
/provider
# Output:
# Current provider : openai
# Model            : gpt-5
# API key          : yes

# 4. (Optional) Update default model
/provider model openai gpt-4o
```

### Workflow 4: Create Custom Instructions

```
# 1. Create AGENTS.md in workspace root

# 2. Write custom Planner instructions
# Example:
# ## Planner Instructions
# You are coordinating data analysis research...

# 3. Reload via REPL
/reload

# Planner now uses custom instructions
```

### Workflow 5: Programmatic Execution

```python
from cognieda.runtime import Application
from cognieda.schemas.artifacts import Task, Objective
from cognieda.execution import Capability, ExecutionRequest, ExecutorInput

# Create request
task = Task(
    objective_id=objective_id,
    kind=TaskKind.DATA,
    instruction="Profile the dataset"
)

request = ExecutionRequest(
    capability=Capability.DATA_PROFILING,
    input=ExecutorInput(task=task),
    context=ExecutorContext(dataset_path="/path/to/data.csv")
)

# Dispatch
result = await app.dispatcher.dispatch(request)

# Handle result
if result.status == ExecutionStatus.SUCCEEDED:
    print(f"Work {result.work_id} completed")
else:
    print(f"Failed: {result.failure.message}")
```

---

## Part 6: Configuration Files Reference

### project.toml

```toml
default_provider = "google"

[providers.google]
type = "google"
model = "gemini-2.5-flash"
api_key_env = "GOOGLE_API_KEY"
base_url = ""

[providers.openai]
type = "openai"
model = "gpt-5"
api_key_env = "OPENAI_API_KEY"
base_url = ""

[providers.anthropic]
type = "anthropic"
model = "claude-sonnet-4"
api_key_env = "ANTHROPIC_API_KEY"
base_url = ""
```

### agents.toml

```toml
[planner]
# skills = ["memory_management", "task_planning"]
# mcp = ["filesystem"]

[data_explorer]
# skills = []
# mcp = []

[hypothesis_analyst]
# skills = ["statistical_analysis"]
# mcp = []

[graph_miner]
# skills = ["graph_analysis"]
# mcp = ["neo4j"]
```

### skills.toml

```toml
[memory_management]
directories = ["./skills/memory"]
description = "Manage session frames, assumptions, and context"
defer_loading = false
validate = true
max_depth = 3
auto_reload = false

[task_planning]
directories = ["./skills/planning"]
description = "Break down analytical goals into executable tasks"
defer_loading = false
validate = true
max_depth = 3
```

### mcp.toml

```toml
[filesystem]
transport = "stdio"
command = "uvx"
args = ["mcp-server-filesystem"]

[neo4j]
transport = "http"
url = "http://localhost:8000/mcp"

[custom_service]
transport = "stdio"
command = "python"
args = ["-m", "custom_mcp_server"]
env = { "API_KEY" = "your-key-here" }
```

### .env (workspace)

```
GOOGLE_API_KEY=your_key_here
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Part 7: Error Handling

### Common Errors

#### MissingModelCredentialError

**Cause**: API key not configured for selected provider

**Message**: `Environment variable '{api_key_env}' is not set.`

**Resolution**:
```
/provider key <profile>
# Or set environment variable
export GOOGLE_API_KEY="..."
```

#### CapabilityNotRegisteredError

**Cause**: Dispatcher cannot find provider for capability

**Message**: `No provider registered for capability: {capability}`

**Resolution**:
- Check ExecutorRegistry has provider registered
- Verify capability spelling
- Check bootstrap includes all necessary providers

#### PlannerErrorCode.INVALID_REQUEST

**Cause**: Empty user message

**Resolution**: Provide non-empty message text

#### PlannerErrorCode.MODEL_UNAVAILABLE

**Cause**: Model credentials not configured

**Resolution**:
```
/provider key <profile>
```

#### PlannerErrorCode.INVALID_MODEL_RESULT

**Cause**: Planner output failed validation

**Resolution**:
- Check custom AGENTS.md for correctness
- Verify /reload worked
- Check model output format

---

## Part 8: Database Operations

### SQLModel Sessions

```python
from cognieda.infrastructure.persistence.session import get_session

# Get database session
with get_session() as session:
    # Perform operations
    result = session.exec(
        select(ObjectiveRecord).where(
            ObjectiveRecord.objective_id == objective_id
        )
    ).first()
```

### Repository Pattern

```python
from cognieda.infrastructure.persistence.repositories import (
    ObjectiveRepository,
    TaskRepository
)

# Create repository
objective_repo = ObjectiveRepository(session)

# Query
objective = objective_repo.get_by_id(objective_id)

# List
objectives = objective_repo.list()

# Create
new_objective = objective_repo.create(objective_data)
```

### Transaction Boundaries

```python
from cognieda.application.services.planner_commit import commit_planner_operations

# Atomic commit
result = commit_planner_operations(
    session,
    session_id="session_123",
    operation_ids=[op1_id, op2_id]
)

if result.success:
    print("Committed successfully")
else:
    print(f"Failed: {result.errors}")
```

---

## Part 9: Testing Utilities

### Fixtures (conftest.py)

```python
import pytest
from pathlib import Path

@pytest.fixture
def workspace_dir(tmp_path):
    """Temporary workspace directory"""
    return tmp_path

@pytest.fixture
def workspace(workspace_dir):
    """Initialized workspace"""
    from cognieda.runtime import Workspace
    return Workspace.open(workspace_dir)

@pytest.fixture
def model_config():
    """Mock model configuration"""
    from cognieda.application.ports import ModelConfig
    return ModelConfig(
        provider="openai",
        model_name="gpt-4",
        api_key="mock-key"
    )
```

### Example Test

```python
@pytest.mark.asyncio
async def test_application_submit_message(app):
    """Test message submission"""
    message = "What's in the data?"
    result = await app.submit_message(message)
    
    assert result.type == MessageType.TEXT
    assert result.role == MessageRole.ASSISTANT
    assert len(result.content) > 0
```

---

## Part 10: Development Commands

### Setup

```bash
# Install dependencies
uv sync

# Install editable tool
uv tool install --editable .

# Copy environment template
copy .env.example .env

# Set API key
echo "GOOGLE_API_KEY=your_key" >> .env
```

### Run

```bash
# Launch REPL
cognieda

# Launch with specific workspace
cognieda /path/to/workspace

# Launch mock mode
cognieda --mode mock
```

### Testing

```bash
# Run all tests
uv run pytest

# Run specific test
uv run pytest tests/agents/planner/test_agent.py

# Run with coverage
uv run pytest --cov=src/cognieda
```

### Linting

```bash
# Check code style
uv run ruff check .

# Format code
uv run ruff format .

# Type check
uv run mypy src/cognieda
```

### Verify All

```bash
# Run all checks
uv run pytest
uv run ruff check .
uv run mypy src/cognieda
```

---

## Part 11: Troubleshooting

### Issue: "Environment variable 'GOOGLE_API_KEY' is not set"

**Solution**:
```bash
export GOOGLE_API_KEY="your_key_here"
# Or use REPL command
/provider key google
```

### Issue: "No provider registered for capability"

**Solution**:
- Check bootstrap includes all necessary providers
- Verify ExecutorRegistry registration
- Check capability spelling

### Issue: Planner instructions not updating

**Solution**:
```
/reload
```

### Issue: Skill not available after registration

**Solution**:
```
/skill use planner skill_name
# This triggers reload with skill assignment
```

### Issue: Database locked error

**Solution**:
- Ensure only one process accesses database
- Check COGNIEDA_DB_URL configuration
- Wait for other operations to complete

---

## Part 12: Performance Tuning

### Conversation History

Long sessions accumulate ConversationHistory:
- Impacts each Planner invocation
- Consider pruning for very long sessions
- Append-only design prevents deletion (intentional)

### Provider Instances

Lazy caching reuses provider instances:
- First request: instantiate provider
- Subsequent requests: use cached instance
- Configuration change: recreate instance

### Database

SQLite suitable for development:
- Consider PostgreSQL for production
- Set COGNIEDA_DB_URL for alternative databases
- Index frequently-queried columns

---

## Part 13: Integration Examples

### Integration with External System

```python
from cognieda.runtime import bootstrap_application
from pathlib import Path
import asyncio

async def analyze_dataset(workspace_path, query):
    """Integrate CogniEDA analysis"""
    app = bootstrap_application(Path(workspace_path))
    
    result = await app.submit_message(query)
    
    return {
        "response": result.content,
        "type": result.type,
        "role": result.role
    }

# Usage
result = asyncio.run(analyze_dataset(
    "/path/to/workspace",
    "Analyze the customer churn data"
))
```

### Custom Specialist Provider

```python
from cognieda.execution import (
    ExecutorProvider, ExecutionRequest, ExecutionResult,
    ExecutionStatus, Capability
)

class CustomAnalyzer:
    async def run(self, request: ExecutionRequest) -> ExecutionResult:
        try:
            # Perform custom analysis
            result_data = self._analyze(request)
            
            return ExecutionResult(
                source_role="custom_analyzer",
                task_id=request.input.task.task_id,
                work_id="custom:12345",
                status=ExecutionStatus.SUCCEEDED,
                limitations=[]
            )
        except Exception as e:
            return ExecutionResult(
                source_role="custom_analyzer",
                task_id=request.input.task.task_id,
                work_id="custom:12345",
                status=ExecutionStatus.FAILED,
                failure=ExecutionFailure(
                    code="ANALYSIS_ERROR",
                    message=str(e)
                )
            )

    def _analyze(self, request):
        # Implementation
        pass
```

---

**Generated**: 2026-08-14  
**Scope**: Complete reference for API, schemas, workflows, configuration, testing, troubleshooting  
**Status**: Foundation implemented; deferred = orchestration


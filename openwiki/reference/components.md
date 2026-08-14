---
type: API Reference
title: CogniEDA Components Reference
description: Complete reference guide to CogniEDA components, their responsibilities, key methods, and integration patterns.
tags: [api, reference, components, cli]
---

# CogniEDA Components Reference

## CLI Entrypoints

### cognieda

Main CLI for launching the Planner REPL.

```powershell
cognieda [OPTIONS] [PATH]
```

**Options:**
- `--mode {real,mock}` - Run mode (default: real)
- `PATH` - Workspace root (default: current directory)

**Examples:**
```powershell
cognieda                           # REPL with current directory
cognieda C:\workspace\proj1        # REPL with custom workspace
cognieda --mode mock               # Demo mode (no real API calls)
```

**Environment Variables:**
- `MODEL_API_KEY` - LLM provider API key (required)
- `COGNIEDA_MODEL_PROVIDER` - Provider override (google, openai, anthropic)
- `COGNIEDA_DB_URL` - Database URL (default: workspace-local SQLite)

## Core Classes

### Application

Main orchestration class coordinating all services.

```python
class Application:
    planner: PlannerAgent
    executor: ExecutionDispatcher
    persistence: PersistenceLayer
    llm_factory: LLMFactory
    
    async def load_workspace(workspace_path: str) -> SessionFrame
    async def execute_objective(objective: Objective) -> PlanResult
    async def admit_discovery(evidence: Evidence) -> Discovery
```

**Key Methods:**
- `load_workspace(path)` - Initialize workspace and load state
- `execute_objective(objective)` - Run planning and analysis
- `admit_discovery(evidence)` - Move evidence to discovery
- `resume_session(frame_id)` - Load prior session context

### Planner Agent

Coordinates objectives, generates tasks, and maintains planning state.

```python
class PlannerAgent:
    state: PlanningState
    graph: StateGraph
    
    async def create_objective(intent: str) -> Objective
    async def plan_tasks(objective: Objective) -> TaskDAG
    async def commit_plan(tasks: TaskDAG) -> PlanResult
```

**Key Methods:**
- `create_objective(intent)` - Create research intent
- `plan_tasks(objective)` - Generate task DAG
- `commit_plan(tasks)` - Approve tasks for execution
- `propose_mutation(delta)` - Suggest plan changes

### Data Explorer

Profiles datasets and validates data contracts.

```python
class DataExplorer:
    async def profile_dataset(source: Path) -> DataProfile
    async def validate_contract(data: DataFrame, schema: Schema) -> ValidationResult
    async def analyze_properties(frame: DataFrame) -> PropertyReport
```

**Key Methods:**
- `profile_dataset(source)` - Create immutable DataProfile
- `validate_contract(data, schema)` - Check data quality
- `analyze_properties(frame)` - Generate statistical summary

### Hypothesis Analyst

Generates claims and evaluates them against evidence.

```python
class HypothesisAnalyst:
    async def generate_hypotheses(context: Context) -> List[Hypothesis]
    async def evaluate_claim(hypothesis: Hypothesis, evidence: Evidence) -> Evaluation
    async def propose_discovery(evidence: Evidence) -> Discovery
```

**Key Methods:**
- `generate_hypotheses(context)` - Suggest testable claims
- `evaluate_claim(hypothesis, evidence)` - Judge fit to evidence
- `propose_discovery(evidence)` - Prepare claim for admission

### Graph Miner

Extracts patterns and relationships from data.

```python
class GraphMiner:
    async def extract_relationships(data: DataFrame) -> Graph
    async def mine_patterns(graph: Graph) -> List[Pattern]
    async def find_anomalies(graph: Graph) -> List[Anomaly]
```

**Key Methods:**
- `extract_relationships(data)` - Build relationship graph
- `mine_patterns(graph)` - Identify recurring structures
- `find_anomalies(graph)` - Detect outliers and unusual patterns

## Persistence Layer

### Repositories

All repositories follow the same interface:

```python
class Repository[T]:
    async def save(entity: T) -> T
    async def get(id: str) -> T | None
    async def list(filter: Filter) -> List[T]
    async def delete(id: str) -> None
```

**Repository Types:**
- `ObjectiveRepository` - Research intents
- `HypothesisRepository` - Testable claims
- `EvidenceRepository` - Observed results
- `DiscoveryRepository` - Admitted claims
- `DataProfileRepository` - Dataset snapshots
- `AssumptionRepository` - Planning assumptions
- `TaskRepository` - Task DAG nodes
- `SessionFrameRepository` - Active contexts

### Database Session

```python
class DatabaseSession:
    async def connect() -> Session
    async def close() -> None
    async def begin_transaction() -> Transaction
```

**Usage:**
```python
async with DatabaseSession.connect() as session:
    objective = await ObjectiveRepository.save(session, new_objective)
```

## Execution Layer

### Execution Dispatcher

Routes work to appropriate specialists.

```python
class ExecutionDispatcher:
    async def dispatch(task: Task, capabilities: Capabilities) -> ExecutionResult
    async def track_execution(run_id: str) -> ExecutionRun
    async def cancel_execution(run_id: str) -> None
```

**Key Methods:**
- `dispatch(task, capabilities)` - Route work to specialist
- `track_execution(run_id)` - Monitor running job
- `cancel_execution(run_id)` - Stop execution

### Capabilities Registry

Declares what work can be executed.

```python
class CapabilitiesRegistry:
    def register_capability(name: str, handler: Callable) -> None
    def list_capabilities() -> List[Capability]
    def get_capability(name: str) -> Capability | None
```

## Schemas

### First-Class Objects (FCOs)

```python
@dataclass
class Objective:
    id: str
    intent: str
    created_at: datetime
    scope: str
    authority: str

@dataclass
class Hypothesis:
    id: str
    claim: str
    objective_id: str
    created_at: datetime
    validity: ValidityState

@dataclass
class Evidence:
    id: str
    result: dict
    analysis_id: str
    created_at: datetime
    provenance: Provenance

@dataclass
class Discovery:
    id: str
    claim: str
    evidence_ids: List[str]
    admitted_at: datetime
    authority: str
```

### Supporting Objects

```python
@dataclass
class DataProfile:
    id: str
    source: str
    columns: List[ColumnProfile]
    row_count: int
    created_at: datetime

@dataclass
class Assumption:
    id: str
    statement: str
    scope: str
    validity: ValidityState

@dataclass
class Task:
    id: str
    objective_id: str
    description: str
    dependencies: List[str]
    status: TaskStatus

@dataclass
class SessionFrame:
    id: str
    active_objective_id: str
    eligible_evidence_ids: List[str]
    context_entries: List[str]
    created_at: datetime
```

## Configuration Files

### project.toml

Workspace-level configuration in `.cognieda/project.toml`:

```toml
[model]
provider = "google"  # or "openai", "anthropic"

[llm]
temperature = 0.7
max_tokens = 2000
top_p = 0.95

[execution]
timeout = 300  # seconds
max_parallel = 4

[persistence]
# Uses workspace-local SQLite by default
# Override with COGNIEDA_DB_URL
```

### Environment Variables

```powershell
MODEL_API_KEY=sk-...                    # LLM API key (required)
COGNIEDA_MODEL_PROVIDER=openai          # Provider override
COGNIEDA_DB_URL=sqlite:///db.db         # Database URL
COGNIEDA_LOG_LEVEL=debug                # Logging level
```

## Integration Patterns

### Adding a Custom Agent

```python
from cognieda.agents import SpecialistAgent
from cognieda.execution import Capabilities

class CustomAgent(SpecialistAgent):
    @property
    def capabilities(self) -> Capabilities:
        return Capabilities(name="custom", tools=["analyze", "report"])
    
    async def process(self, task: Task) -> Evidence:
        # Your analysis logic
        return Evidence(...)
```

Register in dispatcher:
```python
dispatcher.register_agent("custom", CustomAgent())
```

### Adding Tool Capabilities

```python
from cognieda.execution import ExecutionRegistry

registry = ExecutionRegistry()

async def my_tool(data: DataFrame) -> dict:
    # Your tool logic
    return result

registry.register_capability("my_tool", my_tool)
```

### Custom LLM Provider

```python
from cognieda.infrastructure.llm import LLMFactory

class CustomLLMFactory(LLMFactory):
    def create_client(self, provider: str, api_key: str) -> LLMClient:
        if provider == "custom":
            return CustomLLMClient(api_key)
        return super().create_client(provider, api_key)
```

## Error Handling

### Common Exceptions

```python
class CogniEDAException(Exception):
    """Base exception"""

class InvalidStateTransition(CogniEDAException):
    """Authority violation"""

class ValidationError(CogniEDAException):
    """Data contract violation"""

class ExecutionError(CogniEDAException):
    """Analysis execution failed"""

class PersistenceError(CogniEDAException):
    """Database operation failed"""
```

### Error Recovery

```python
try:
    result = await execution.dispatch(task)
except ExecutionError as e:
    logger.error(f"Execution failed: {e}")
    # Task will be retried or user prompted
except ValidationError as e:
    logger.error(f"Data invalid: {e}")
    # User must provide correct data
```

## Testing Utilities

### Mock Application

```python
from cognieda.cli.mock_application import MockApplication

app = MockApplication()
await app.execute_objective(test_objective)
```

### Test Database

```python
from cognieda.infrastructure.persistence import init_test_db

async with init_test_db() as session:
    repo = ObjectiveRepository(session)
    saved = await repo.save(test_objective)
```

### Agent Mocking

```python
from unittest.mock import AsyncMock

mock_planner = AsyncMock()
mock_planner.plan_tasks.return_value = test_dag
```

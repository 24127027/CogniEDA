---
type: Development Guide
title: CogniEDA Development Setup and Contribution Guide
description: Instructions for setting up a development environment, running tests, contributing code, and understanding the development workflow.
tags: [development, setup, testing, contribution]
---

# Development Setup and Contribution Guide

## Development Environment Setup

### Prerequisites

- Python 3.12 or later
- `uv` package manager
- Git
- Your preferred code editor

### Initial Setup

```powershell
# Clone the repository
git clone https://github.com/your-org/CogniEDA.git
cd CogniEDA

# Install dependencies with uv
uv sync

# Install the package in editable mode
uv tool install --editable .

# Update shell environment if needed
uv tool update-shell

# Copy environment template
copy .env.example .env
```

### Configure .env

Set required variables in `.env`:

```
MODEL_API_KEY=your_api_key_here
COGNIEDA_MODEL_PROVIDER=google
COGNIEDA_LOG_LEVEL=debug
```

### Verify Installation

```powershell
# Launch CLI
cognieda --help

# Run verification commands
uv run pytest
uv run ruff check .
uv run mypy src/cognieda
```

## Project Structure

```
CogniEDA/
├── src/cognieda/
│   ├── agents/                 # Specialist implementations
│   │   ├── data_explorer/      # Data profiling & validation
│   │   ├── graph_miner/        # Pattern extraction
│   │   ├── hypothesis_analyst/  # Claim evaluation
│   │   ├── planner/            # Objective coordination
│   │   └── utilities/          # Shared utilities
│   ├── application/            # Core services & orchestration
│   │   ├── ports/              # Interfaces & contracts
│   │   └── services/           # Business logic
│   ├── cli/                    # Command-line interface
│   │   ├── app.py              # CLI entry point
│   │   ├── main.py             # REPL implementation
│   │   └── renderer.py         # Output formatting
│   ├── execution/              # Dispatch & execution
│   │   ├── dispatcher.py        # Task routing
│   │   ├── registry.py          # Capability registry
│   │   └── contracts.py         # Execution interfaces
│   ├── infrastructure/         # External integrations
│   │   ├── llm/                # Model factory
│   │   ├── persistence/        # Database & ORM
│   │   ├── datasets/           # Data loading
│   │   ├── skills/             # MCP skills
│   │   └── mcp/                # MCP protocol
│   ├── runtime/                # Execution runtime
│   │   ├── application.py       # App orchestration
│   │   ├── bootstrap.py         # Initialization
│   │   ├── conversation.py      # Message handling
│   │   └── workspace.py         # Workspace management
│   └── schemas/                # Data models
│       ├── plan.py             # Planning schemas
│       ├── common.py            # Shared types
│       ├── artifacts.py         # FCO definitions
│       └── enums.py             # Enumerations
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── fixtures/               # Test data & mocks
├── docs/                       # Source documentation
├── openwiki/                   # Generated wiki
├── config/                     # Configuration templates
└── pyproject.toml              # Package metadata
```

## Development Workflow

### Creating a Feature Branch

```powershell
# Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# Make your changes
# Commit regularly with clear messages
git add .
git commit -m "Clear description of change"
```

### Testing

#### Run All Tests

```powershell
uv run pytest
uv run pytest --cov=src/cognieda --cov-report=html
```

#### Run Specific Tests

```powershell
# Single test file
uv run pytest tests/unit/test_planner.py

# Single test
uv run pytest tests/unit/test_planner.py::test_create_objective

# By marker
uv run pytest -m "unit"
uv run pytest -m "integration"
```

#### Test Organization

- **Unit tests**: `tests/unit/` - No external dependencies
- **Integration tests**: `tests/integration/` - Database, APIs
- **Fixtures**: `tests/fixtures/` - Shared test data

### Code Quality

#### Linting with Ruff

```powershell
# Check code
uv run ruff check src/cognieda tests

# Fix automatically
uv run ruff check --fix src/cognieda tests
```

#### Type Checking with mypy

```powershell
uv run mypy src/cognieda
```

#### Pre-commit

```powershell
# All checks before commit
uv run ruff check . && uv run mypy src/cognieda && uv run pytest
```

### Git Workflow

#### Before Submitting PR

```powershell
# Update from main
git fetch origin
git rebase origin/main

# Run full test suite
uv run pytest
uv run ruff check .
uv run mypy src/cognieda

# Commit and push
git push origin feature/your-feature-name
```

#### Create Pull Request

- Provide clear title and description
- Link related issues
- Ensure CI passes
- Request code review

## Adding a New Component

### Adding a New Specialist Agent

1. Create agent directory:
   ```
   src/cognieda/agents/my_agent/
   ├── __init__.py
   ├── agent.py        # SpecialistAgent implementation
   ├── state.py        # Agent state schema
   └── graph.py        # LangGraph workflow (if needed)
   ```

2. Implement SpecialistAgent:
   ```python
   from cognieda.execution import SpecialistAgent, Capabilities
   
   class MyAgent(SpecialistAgent):
       @property
       def capabilities(self) -> Capabilities:
           return Capabilities(name="my_agent", tools=["tool1", "tool2"])
       
       async def process(self, task: Task) -> Evidence:
           # Implementation
           pass
   ```

3. Register in dispatcher:
   ```python
   # In execution/registry.py
   from cognieda.agents.my_agent import MyAgent
   
   AGENTS = {
       "my_agent": MyAgent(),
   }
   ```

4. Add tests:
   ```python
   # tests/unit/agents/test_my_agent.py
   @pytest.mark.asyncio
   async def test_my_agent_process():
       agent = MyAgent()
       result = await agent.process(test_task)
       assert result.is_valid()
   ```

### Adding a New Repository

1. Create repository class:
   ```python
   # src/cognieda/infrastructure/persistence/repositories/my_entity_repository.py
   from cognieda.infrastructure.persistence.common import BaseRepository
   
   class MyEntityRepository(BaseRepository[MyEntity]):
       async def save(self, session, entity: MyEntity) -> MyEntity:
           # Implementation
       
       async def get(self, session, id: str) -> MyEntity | None:
           # Implementation
   ```

2. Add database model:
   ```python
   # src/cognieda/infrastructure/persistence/models.py
   class MyEntityModel(SQLModel, table=True):
       id: str = Field(primary_key=True)
       # fields...
   ```

3. Register in session:
   ```python
   # src/cognieda/infrastructure/persistence/session.py
   from .repositories.my_entity_repository import MyEntityRepository
   
   class DatabaseSession:
       my_entities = MyEntityRepository()
   ```

### Adding Configuration Options

1. Update `.env.example`:
   ```
   MY_NEW_OPTION=default_value
   ```

2. Update schema in workspace:
   ```toml
   # .cognieda/project.toml
   [my_tool]
   option1 = "value"
   ```

3. Load in runtime:
   ```python
   # src/cognieda/runtime/bootstrap.py
   config = load_config("my_tool")
   my_tool_instance.configure(config)
   ```

## Testing Best Practices

### Unit Test Template

```python
import pytest
from cognieda.agents.my_agent import MyAgent
from cognieda.schemas import Task, Evidence

@pytest.mark.asyncio
class TestMyAgent:
    @pytest.fixture
    def agent(self):
        return MyAgent()
    
    @pytest.fixture
    def test_task(self):
        return Task(
            id="test-1",
            objective_id="obj-1",
            description="Test task"
        )
    
    async def test_process_success(self, agent, test_task):
        result = await agent.process(test_task)
        
        assert isinstance(result, Evidence)
        assert result.analysis_id == test_task.id
        assert result.provenance is not None
    
    async def test_process_invalid_input(self, agent):
        with pytest.raises(ValueError):
            await agent.process(None)
```

### Integration Test Template

```python
import pytest
from cognieda.runtime import Application

@pytest.mark.integration
@pytest.mark.asyncio
class TestEndToEnd:
    @pytest.fixture
    async def app(self):
        app = Application()
        await app.initialize()
        yield app
        await app.shutdown()
    
    async def test_full_workflow(self, app):
        # Create objective
        objective = await app.create_objective("Analyze data")
        assert objective.id is not None
        
        # Plan tasks
        tasks = await app.plan_tasks(objective)
        assert len(tasks) > 0
        
        # Execute and verify
        result = await app.execute_plan(tasks)
        assert result.success
```

## Documentation

### Adding Documentation

1. Create or update markdown in `openwiki/`
2. Start with OKF front matter (see example below)
3. Use clear headings and code blocks
4. Link to related pages

### OKF Front Matter Template

```markdown
---
type: Component Description
title: Human-Readable Title
description: One to two sentence summary optimized for search.
tags: [tag1, tag2, tag3]
---

# Main Content
```

### Style Guide

- Use active voice
- Keep paragraphs concise
- Use code blocks for all code examples
- Link to related documentation
- Include examples when teaching concepts

## Debugging

### Enable Debug Logging

```powershell
$env:COGNIEDA_LOG_LEVEL = "debug"
cognieda
```

### Debug Agent Execution

```python
# In your test or script
import logging
logging.basicConfig(level=logging.DEBUG)

agent = MyAgent()
result = await agent.process(task)
```

### Inspect Database State

```python
from cognieda.infrastructure.persistence import DatabaseSession

async with DatabaseSession.connect() as session:
    objectives = await session.objectives.list(session)
    for obj in objectives:
        print(f"Objective: {obj.intent}")
```

### Mock Application for Testing

```powershell
cognieda --mode mock
```

This runs without real LLM calls, using mock responses.

## Release Process

1. Update version in `pyproject.toml`
2. Update CHANGELOG
3. Create release branch
4. Run full test suite
5. Tag release
6. Create GitHub release

## Getting Help

- Check existing issues and discussions
- Read architecture docs in `docs/`
- Review test examples in `tests/`
- Ask in project discussions

## Common Issues

### Issue: "Module not found" error

**Solution**: Run `uv sync` to install all dependencies

### Issue: Tests fail with database locked

**Solution**: Delete `.cognieda/.cognieda.db` and retry

### Issue: mypy errors on valid code

**Solution**: Check `pyproject.toml` mypy config; may need type stubs

### Issue: ruff wants to reformat code

**Solution**: Run `uv run ruff check --fix .` to auto-format

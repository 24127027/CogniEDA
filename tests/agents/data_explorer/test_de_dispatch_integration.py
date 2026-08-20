from __future__ import annotations

import asyncio
import os
from pathlib import Path
from uuid import uuid4

import pytest
from dotenv import load_dotenv

from cognieda.agents.data_explorer.agent import DataExplorer
from cognieda.agents.data_explorer.contracts import DataExplorerInput
from cognieda.application.ports.llm import ModelConfig
from cognieda.delegation.contracts import (
    Capability,
    ExecutionRequest,
    ExecutionStatus,
    ExecutorContext,
    ExecutorInput,
)
from cognieda.delegation.dispatcher import ExecutorDispatcher
from cognieda.delegation.registry import ExecutorRegistry
from cognieda.infrastructure.llm import AgentFactory
from cognieda.runtime.workspace import Workspace
from cognieda.schemas.artifacts import Task
from cognieda.schemas.enums import TaskKind


@pytest.fixture(autouse=True)
async def delay_between_analysis(request):
    """Add a delay between tests to respect Gemini free tier limits (5 req/min)."""
    # Only delay for the parameterized data analysis test
    if request.node.originalname == "test_end_to_end_data_analysis_tools":
        await asyncio.sleep(60)
        yield
    else:
        yield


@pytest.fixture(scope="module")
def dispatcher(tmp_path_factory):
    # Setup temporary workspace to avoid writing db/state to the real workspace
    workspace_path = tmp_path_factory.mktemp("workspace")
    workspace = Workspace.open(workspace_path)
    
    # Load .env from the real project root to get API keys
    real_root = Path(__file__).resolve().parents[3]
    load_dotenv(real_root / ".env")
    
    # Dynamically configure the LLM model from the user's .env file
    model_config = ModelConfig(
        provider=os.environ.get("COGNIEDA_MODEL_PROVIDER", "google"),
        model_name=os.environ.get("COGNIEDA_MODEL_NAME", "gemini-3.5-flash-lite"),
        base_url=os.environ.get("MODEL_BASE_URL", ""),
        api_key=os.environ.get("MODEL_API_KEY", "")
    )
    
    agent_factory = AgentFactory(tooling_config=workspace)
    
    registry = ExecutorRegistry()
    registry.register(
        lambda: DataExplorer(config=model_config, agent_factory=agent_factory)
    )
    return ExecutorDispatcher(registry)


@pytest.fixture(scope="module")
def dataset_path(request):
    # Allow overriding via command line option
    dataset_opt = request.config.getoption("--dataset")
    if dataset_opt and Path(dataset_opt).exists():
        return str(Path(dataset_opt).resolve())
        
    # Fallback to local offers file if it exists
    local_offers = Path(__file__).parent / "offers-1000.csv"
    if local_offers.exists():
        return str(local_offers)
        
    pytest.skip("Test dataset not found. Use --dataset <path> or place offers-1000.csv in the test directory.")


@pytest.fixture(scope="module")
def live_data_profile(dispatcher, dataset_path):
    # Profile the dataset once for the module to save LLM/execution time.
    request = ExecutionRequest(
        capability=Capability.DATA_PROFILING,
        input=ExecutorInput(
            task=Task(
                objective_id=uuid4(),
                kind=TaskKind.DATA,
                instruction="Profile the dataset.",
            )
        ),
        context=ExecutorContext(dataset_path=dataset_path),
    )
    result = asyncio.run(dispatcher.dispatch(request))
    assert result.status == ExecutionStatus.SUCCEEDED, f"Profiling failed: {getattr(result, 'failure', result)}"
    return result.produced_data_profile


@pytest.mark.llm
@pytest.mark.anyio
async def test_end_to_end_data_profiling_dispatch(dispatcher, dataset_path):
    request = ExecutionRequest(
        capability=Capability.DATA_PROFILING,
        input=ExecutorInput(
            task=Task(
                objective_id=uuid4(),
                kind=TaskKind.DATA,
                instruction="Profile the dataset.",
            )
        ),
        context=ExecutorContext(dataset_path=dataset_path),
    )

    result = await dispatcher.dispatch(request)
    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.produced_data_profile is not None
    assert result.produced_data_profile.row_count == 1000
    assert result.produced_data_profile.column_count == 4


@pytest.mark.llm
@pytest.mark.anyio
@pytest.mark.parametrize(
    "instruction",
    [
        "Count the total number of rows in the dataset.",
        "Check for missing values in the 'price' and 'stock' columns.",
        "Provide a distribution summary of the 'price' column.",
        "Calculate the correlation matrix between 'price' and 'stock'.",
        "Perform a t-test to check if 'price' is significantly different from 0.",
        "Group the dataset by 'stock' and calculate the mean of 'price'."
    ],
)
async def test_end_to_end_data_analysis_tools(
    dispatcher, dataset_path, live_data_profile, instruction
):
    request = ExecutionRequest(
        capability=Capability.DATA_ANALYSIS,
        input=DataExplorerInput(
            task=Task(
                objective_id=uuid4(),
                kind=TaskKind.DATA,
                instruction=instruction,
            ),
            data_profile=live_data_profile,
        ),
        context=ExecutorContext(dataset_path=dataset_path),
    )

    result = await dispatcher.dispatch(request)
    
    assert result.status == ExecutionStatus.SUCCEEDED, f"Execution failed: {result.failure}"
    assert len(result.observations) > 0
    # Every successful analysis operation produces at least one piece of semantic_evidence
    assert result.observations[0].observation_type == "semantic_evidence"

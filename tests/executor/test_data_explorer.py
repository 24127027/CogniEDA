from __future__ import annotations

import asyncio
from uuid import UUID

import pandas as pd

from agents.executor import ExecutorContext, ExecutorInput
from agents.executor.data_explorer.agent import DataExplorer
from schemas.artifacts import Task
from schemas.enums import TaskKind


def _task(*, description: str, evidence_expectation: str) -> Task:
	return Task(
		title="Inspect dataset",
		description=description,
		task_kind=TaskKind.ANALYTICAL,
		profile_id=UUID("11111111-1111-1111-1111-111111111111"),
		variables=["value"],
		evidence_expectation=evidence_expectation,
	)


def _executor() -> DataExplorer:
	def admit(_: object) -> bool:
		return True

	return DataExplorer(mock_admission_call=admit)


def test_data_explorer_exploration_path_returns_evidence(tmp_path, monkeypatch) -> None:
	dataframe = pd.DataFrame({"value": [1, 2, 3], "group": ["a", "b", "a"]})
	dataset_path = tmp_path / "exploration.csv"
	dataframe.to_csv(dataset_path, index=False)
	monkeypatch.setenv("COGNIEDA_DE_DATASET_PATH", str(dataset_path))

	executor = _executor()
	result = asyncio.run(
		executor.run(
			input=ExecutorInput(
				task=_task(
					description="Report the row count and column names for this dataset.",
					evidence_expectation="row_count",
				),
			),
			context=ExecutorContext(),
		)
	)

	assert result.evidence_draft is not None
	assert result.evidence_drafts
	assert result.data_profile_draft is None
	assert result.execution_logs == []
	assert result.final_result is not None
	assert "final_result" not in result.final_result
	assert result.final_result["evidence_draft"]["evidence_id"] == str(result.evidence_draft.evidence_id)


def test_data_explorer_profiling_path_returns_data_profile(tmp_path, monkeypatch) -> None:
	dataframe = pd.DataFrame({"value": [1, 1, None], "group": ["a", "a", "b"]})
	dataset_path = tmp_path / "profiling.csv"
	dataframe.to_csv(dataset_path, index=False)
	monkeypatch.setenv("COGNIEDA_DE_DATASET_PATH", str(dataset_path))

	executor = _executor()
	result = asyncio.run(
		executor.run(
			input=ExecutorInput(
				task=_task(
					description="Profile and clean the dataset before returning a profile summary.",
					evidence_expectation="profile",
				),
			),
			context=ExecutorContext(),
		)
	)

	assert result.data_profile_draft is not None
	assert result.evidence_drafts == []
	assert result.evidence_draft is None
	assert result.execution_logs == []
	assert result.final_result is not None
	assert "final_result" not in result.final_result
	assert result.final_result["data_profile_draft"]["dataset_path"] == str(dataset_path)
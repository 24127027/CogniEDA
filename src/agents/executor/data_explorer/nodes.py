from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field, ValidationError

from agents.llm import ModelConfig
from data import DatasetProfiler, load_dataset
from schemas.artifacts import DataProfile, Task
from schemas.enums import DataProfileMethod

from ..capabilities import Capability
from ..types import ExecutionFailure, ExecutionStatus
from .state import State
from .types import DataExplorerObservation, DataExplorerResult

_MAX_LOGICAL_RETRIES = 2
_MAX_CODE_RETRIES = 2


class _GeneratedCodeDraft(BaseModel):
    python_code: str = Field(min_length=1)
    result_summary: str | None = None


def _task(state: State) -> Task:
	task = state["request"].input.task
	return task


def _task_text(state: State) -> str:
	task = _task(state)
	return f"{task.title}\n{task.description}\n{task.evidence_expectation or ''}"


def _context_value(state: State, name: str, default: Any = None) -> Any:
	return getattr(state["request"].context, name, default)


def _dataset_path(state: State) -> str | None:
	dataset_path = _context_value(state, "dataset_path")
	if dataset_path:
		return str(dataset_path)

	profile = _context_value(state, "data_profile")
	if isinstance(profile, DataProfile):
		return profile.dataset_path

	return os.environ.get("COGNIEDA_DE_DATASET_PATH") or None


def _load_dataframe(state: State) -> pd.DataFrame:
	dataframe = _context_value(state, "dataframe")
	if isinstance(dataframe, pd.DataFrame):
		return dataframe.copy()

	dataset_path = _dataset_path(state)
	if dataset_path is None:
		raise RuntimeError("Data Explorer requires a dataset_path or dataframe on context.")

	return load_dataset(dataset_path).dataframe.copy()


def _prompt_for_code(state: State) -> str:
	return (
		"Generate Python that answers the atomic dataset request using the provided `dataframe`.\n"
		"Return a JSON-serializable dict assigned to `result`.\n"
		"Use only local variables and do not persist anything.\n"
		f"Task text:\n{_task_text(state)}\n"
		f"Current logs: {json.dumps(state['execution_logs'])}"
	)


def _fallback_code(state: State) -> str:
	return (
		"result = {\n"
		"    'row_count': int(len(dataframe)),\n"
		"    'column_names': [str(column) for column in dataframe.columns.tolist()],\n"
		"    'preview_rows': dataframe.head(5).to_dict(orient='records'),\n"
		"}"
	)


def _safe_agent_output(config: ModelConfig, prompt: str) -> _GeneratedCodeDraft | None:
	from .agent import create_de_agent

	try:
		agent = create_de_agent(config)
	except ValueError:
		return None

	try:
		result = agent.run_sync(prompt, output_type=_GeneratedCodeDraft)
	except Exception:
		return None

	try:
		return _GeneratedCodeDraft.model_validate(result.output)
	except ValidationError:
		return None


def _run_python(code: str, dataframe: pd.DataFrame) -> Any:
	namespace: dict[str, Any] = {
		"dataframe": dataframe,
		"pd": pd,
		"result": None,
	}
	exec(compile(code, "<data_explorer>", "exec"), namespace, namespace)
	return namespace.get("result")


def _result_text(raw_data_results: Any) -> str:
	if isinstance(raw_data_results, str):
		return raw_data_results
	try:
		return json.dumps(raw_data_results, default=str).lower()
	except TypeError:
		return str(raw_data_results).lower()


def _results_match_request(state: State) -> bool:
	raw_data_results = state["raw_data_results"]
	if raw_data_results is None:
		return False

	if isinstance(raw_data_results, Mapping):
		if raw_data_results.get("semantic_match") is True:
			return True
		if raw_data_results.get("fatal_mismatch") is True:
			return False

	request_text = _task_text(state).lower()
	result_text = _result_text(raw_data_results)
	expected_tokens = [
		token
		for token in (
			_task(state).evidence_expectation,
			_task(state).title,
			_task(state).description,
		)
		if isinstance(token, str) and token.strip()
	]

	if any(token.lower() in result_text for token in expected_tokens):
		return True

	if any(token in request_text for token in ("row", "count", "summary", "distribution")):
		return isinstance(raw_data_results, Mapping) and any(
			key in raw_data_results for key in ("row_count", "summary", "column_names")
		)

	return False


def _is_recoverable_mismatch(raw_data_results: Any) -> bool:
	if isinstance(raw_data_results, Mapping):
		return raw_data_results.get("recoverable_mismatch") is True
	return False


def route_results(state: State, runtime: Any = None) -> str:
	if _results_match_request(state):
		return "draft_observation"
	if (
		_is_recoverable_mismatch(state["raw_data_results"])
		and state["retry_count"] < _MAX_LOGICAL_RETRIES
	):
		return "generate_and_execute_code"
	return "handle_failure_and_logs"


def _build_observation(state: State) -> DataExplorerObservation:
	raw_data_results = state["raw_data_results"]
	if isinstance(raw_data_results, Mapping):
		summary_text = str(raw_data_results.get("summary") or raw_data_results)
		payload = dict(raw_data_results)
	else:
		summary_text = str(raw_data_results)
		payload = {"value": raw_data_results}

	return DataExplorerObservation(
		observation_type="bounded_data_analysis",
		summary=summary_text,
		payload=payload,
	)


def _build_profile_draft(state: State, dataframe: pd.DataFrame) -> DataProfile:
	dataset_path = _dataset_path(state)
	if dataset_path is None:
		raise RuntimeError("Data profiling requires a dataset_path on executor context.")

	cleaned_dataframe = dataframe.drop_duplicates().copy()
	if any("missing" in log.lower() for log in state["execution_logs"]):
		cleaned_dataframe = cleaned_dataframe.dropna(how="all")

	profiler = DatasetProfiler()
	return profiler.profile_dataframe(
		cleaned_dataframe,
		dataset_path=dataset_path,
		method=DataProfileMethod.DATA_QUALITY_SCAN,
	)


def route_request(state: State, runtime: Any = None) -> str:
	if state["request"].capability == Capability.DATA_PROFILING:
		return "execute_profiling_and_cleaning"
	return "generate_and_execute_code"


def generate_and_execute_code(
	state: State, runtime: Any = None, *, agent_config: ModelConfig
) -> State:
	logs = list(state["execution_logs"])
	dataframe = _load_dataframe(state)

	for attempt in range(_MAX_CODE_RETRIES + 1):
		prompt = _prompt_for_code(state)
		draft = _safe_agent_output(agent_config, prompt)
		code = draft.python_code if draft is not None else _fallback_code(state)
		try:
			raw_data_results = _run_python(code, dataframe)
			return {
				**state,
				"raw_data_results": raw_data_results,
				"execution_logs": logs,
			}
		except Exception as exc:
			logs.append(f"Generated code attempt {attempt + 1} failed: {exc}")

	logs.append("Native code retries exhausted before producing raw_data_results.")
	return {**state, "raw_data_results": None, "execution_logs": logs}


def evaluate_results(state: State, runtime: Any = None) -> State:
	logs = list(state["execution_logs"])
	raw_data_results = state["raw_data_results"]

	if raw_data_results is None:
		logs.append("Data Explorer could not produce raw data results.")
		return {**state, "execution_logs": logs}

	if _results_match_request(state):
		return {**state, "execution_logs": logs}

	if _is_recoverable_mismatch(raw_data_results) and state["retry_count"] < _MAX_LOGICAL_RETRIES:
		logs.append("Raw data output was close but did not satisfy the atomic request.")
		return {
			**state,
			"retry_count": state["retry_count"] + 1,
			"execution_logs": logs,
		}

	logs.append("Raw data output failed semantic evaluation for the atomic request.")
	return {**state, "execution_logs": logs}


def draft_observation(state: State, runtime: Any = None) -> State:
	return {**state, "observation": _build_observation(state)}


def execute_profiling_and_cleaning(
	state: State,
	runtime: Any = None,
	*,
	agent_config: ModelConfig,
) -> State:
	logs = list(state["execution_logs"])

	try:
		dataframe = _load_dataframe(state)
		profile_draft = _build_profile_draft(state, dataframe)
		return {
			**state,
			"data_profile_draft": profile_draft,
			"execution_logs": logs,
		}
	except Exception as exc:
		logs.append(f"Profiling and cleaning failed: {exc}")
		return {**state, "data_profile_draft": None, "execution_logs": logs}


def return_profile_draft(state: State, runtime: Any = None) -> State:
	return state


def handle_failure_and_logs(state: State, runtime: Any = None) -> State:
	logs = list(state["execution_logs"])
	if state["raw_data_results"] is None and not any(
		"data explorer could not produce raw data results" in log.lower() for log in logs
	):
		logs.append("Data Explorer terminated before producing usable raw data results.")

	if state["observation"] is None and state["data_profile_draft"] is None:
		logs.append("No role-native output was produced for the caller.")

	return {**state, "execution_logs": logs}


def compile_result(state: State, runtime: Any = None) -> State:
	observations = [state["observation"]] if state["observation"] is not None else []
	data_profile_draft = state["data_profile_draft"]

	execution_run_ref = f"de:{_task(state).task_id}"
	succeeded = bool(observations or data_profile_draft is not None)
	result = DataExplorerResult(
		source_role="data_explorer",
		task_id=_task(state).task_id,
		work_id=execution_run_ref,
		status=ExecutionStatus.SUCCEEDED if succeeded else ExecutionStatus.FAILED,
		failure=(
			None
			if succeeded
			else ExecutionFailure(
				code="no_role_native_output",
				message="Data Explorer produced no role-native output.",
			)
		),
		capability=state["request"].capability,
		observations=observations,
		produced_data_profile=data_profile_draft,
		artifact_refs=[ref for item in observations for ref in item.artifact_refs],
		execution_details=list(state["execution_logs"]),
	)
	return {**state, "final_result": result}

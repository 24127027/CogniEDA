from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field

from agents.llm import ModelConfig
from schemas.artifacts import Discovery, Evidence, Hypothesis
from schemas.common import DiscoveryClaim, ValidityBasis
from schemas.enums import DiscoveryEpistemicStatus

from ..capabilities import Capability
from ..types import ExecutionFailure, ExecutionRequest, ExecutionStatus, ExecutorInput
from .deps import AdmissionCall, DispatcherCall
from .state import HAState
from .types import HypothesisAnalystResult


class _HypothesisDraftModel(BaseModel):
	statement: str
	scope: str
	validation_method: str
	evidence_expectation: str
	variables: list[str] = Field(default_factory=list)


class _EvidenceAssessmentModel(BaseModel):
	outcome: str
	scientific_value: str


def _task(state: HAState):
	return state["request"].input.task


def _task_text(state: HAState) -> str:
	task = _task(state)
	return f"{task.title}\n{task.description}"


def _is_vague_task(task: Any) -> bool:
	if not task.can_generate_hypothesis():
		return True

	text = f"{task.title} {task.description} {task.evidence_expectation or ''}".lower()
	return any(token in text for token in ("maybe", "some", "something", "anything", "data"))


def _safe_agent_output(
	config: ModelConfig, prompt: str, output_type: type[BaseModel]
) -> BaseModel | None:
	from .agent import create_ha_agent

	try:
		agent = create_ha_agent(config)
	except ValueError:
		return None

	try:
		result = agent.run_sync(prompt, output_type=output_type)
	except Exception:
		return None

	return output_type.model_validate(result.output)


def _hypothesis_from_task(task: Any) -> Hypothesis:
	return Hypothesis(
		task_id=task.task_id,
		profile_id=task.profile_id,
		statement=f"{task.title}: {task.evidence_expectation}",
		variables=list(task.variables),
		scope=task.description,
		validation_method="Statistical comparison against the requested evidence expectation.",
		evidence_expectation=task.evidence_expectation,
	)


def _evaluation_outcome_from_evidence(evidence: Sequence[Evidence]) -> tuple[str, str]:
	summary = " ".join(item.result_summary.summary.lower() for item in evidence)
	if any(token in summary for token in ("support", "increase", "confirm", "higher")):
		return "Supported", "valuable knowledge"
	if any(token in summary for token in ("reject", "decrease", "contradict", "lower")):
		return "Rejected", "valuable knowledge"
	return "Inconclusive", "useless noise"


def _build_discovery(
	hypothesis: Hypothesis, evidence: Sequence[Evidence], outcome: str
) -> Discovery:
	evidence_ids = [item.evidence_id for item in evidence]
	supporting_evidence = evidence[0]
	return Discovery(
		hypothesis_id=hypothesis.hypothesis_id,
		evidence_ids=evidence_ids,
		claim=DiscoveryClaim(
			statement=hypothesis.statement,
			scope=hypothesis.scope,
			conditions=list(hypothesis.variables),
			result=outcome,
		),
		epistemic_status=(
			DiscoveryEpistemicStatus.SUPPORTED
			if outcome == "Supported"
			else DiscoveryEpistemicStatus.CONTRADICTED
			if outcome == "Rejected"
			else DiscoveryEpistemicStatus.INCONCLUSIVE
		),
		scope=hypothesis.scope,
		validity_basis=ValidityBasis(
			data_profile_id=hypothesis.profile_id,
			analysis_frame_refs=[supporting_evidence.analysis_frame_ref],
			hypothesis_id=hypothesis.hypothesis_id,
			evidence_ids=evidence_ids,
			method=supporting_evidence.method,
			parameters=list(supporting_evidence.parameters),
			decision_rule="Evidence outcome matched the hypothesis evaluation rule.",
			strength="moderate",
			uncertainty="bounded by available evidence",
		),
	)


def _result_package(state: HAState) -> dict[str, Any]:
	evidence_refs = [str(item.evidence_id) for item in state["collected_evidence"]]
	evidence_drafts = list(state["collected_evidence"])
	discovery_drafts = [state["discovery_draft"]] if state["discovery_draft"] is not None else []
	package = {
		"hypothesis_draft": state["hypothesis_draft"],
		"evidence_drafts": evidence_drafts,
		"discovery_drafts": discovery_drafts,
		"evidence_refs": evidence_refs,
		"execution_logs": list(state["execution_logs"]),
		"evaluation_outcome": state["evaluation_outcome"],
		"scientific_value": state["scientific_value"],
		"execution_run_ref": f"ha:{state['request'].input.task.task_id}",
	}
	return package


def formulate_hypothesis(state: HAState, *, agent_config: ModelConfig) -> dict[str, Any]:
	task = _task(state)
	logs = list(state["execution_logs"])

	if _is_vague_task(task):
		logs.append("Task too vague or complex to form a single hypothesis.")
		return {"execution_logs": logs, "hypothesis_draft": None}

	prompt = (
		"Formulate exactly one mathematically testable hypothesis from this task.\n"
		f"Task:\n{_task_text(state)}\n\n"
		"Return statement, scope, validation_method, evidence_expectation, and variables."
	)
	model_output = _safe_agent_output(agent_config, prompt, _HypothesisDraftModel)
	hypothesis = (
		Hypothesis(
			task_id=task.task_id,
			profile_id=task.profile_id,
			statement=model_output.statement,
			scope=model_output.scope,
			validation_method=model_output.validation_method,
			evidence_expectation=model_output.evidence_expectation,
			variables=list(model_output.variables),
		)
		if model_output is not None
		else _hypothesis_from_task(task)
	)

	return {"hypothesis_draft": hypothesis, "execution_logs": logs}


def plan_de_requests(state: HAState, *, mock_dispatcher_call: DispatcherCall) -> dict[str, Any]:
	if state["hypothesis_draft"] is None:
		return {"de_capability_requests": state["de_capability_requests"]}

	attempts = len(state["de_capability_requests"])
	if attempts >= 2:
		logs = list(state["execution_logs"])
		logs.append("Alternative DE plans exhausted before evidence collection.")
		return {"execution_logs": logs}

	task = _task(state)
	if attempts == 0:
		plan_task = task
	else:
		plan_task = task.model_copy(
			update={
				"description": f"Alternative test plan for: {task.description}",
				"evidence_expectation": f"Alternative evidence for: {task.evidence_expectation}",
			}
		)

	request = ExecutionRequest(
		capability=Capability.DATA_ANALYSIS,
		input=ExecutorInput(task=plan_task),
		context=state["request"].context,
	)
	return {"de_capability_requests": [*state["de_capability_requests"], request]}


def dispatch_to_de(state: HAState, *, mock_dispatcher_call: DispatcherCall) -> dict[str, Any]:
	if not state["de_capability_requests"]:
		return {"collected_evidence": state["collected_evidence"]}

	result = mock_dispatcher_call(state["de_capability_requests"][-1])
	logs = list(state["execution_logs"])
	logs.append(
		f"Data Explorer returned {len(result.observations)} observation(s); "
		"canonical Evidence admission is not implemented."
	)
	return {
		"collected_evidence": state["collected_evidence"],
		"execution_logs": logs,
	}


def evaluate_evidence(state: HAState) -> dict[str, Any]:
	hypothesis = state["hypothesis_draft"]
	if hypothesis is None or not state["collected_evidence"]:
		return {"evaluation_outcome": None, "scientific_value": None}

	prompt = (
		"Evaluate the evidence against the hypothesis and classify the outcome.\n"
		f"Hypothesis: {hypothesis.statement}\n"
		f"Scope: {hypothesis.scope}\n"
		"Evidence summaries: "
		f"{[item.result_summary.summary for item in state['collected_evidence']]}\n"
	)
	model_output = _safe_agent_output(ModelConfig(), prompt, _EvidenceAssessmentModel)
	if model_output is not None:
		return {
			"evaluation_outcome": model_output.outcome,
			"scientific_value": model_output.scientific_value,
		}

	outcome, scientific_value = _evaluation_outcome_from_evidence(state["collected_evidence"])
	return {"evaluation_outcome": outcome, "scientific_value": scientific_value}


def assess_scientific_value(state: HAState) -> dict[str, Any]:
	if state["evaluation_outcome"] is None or state["hypothesis_draft"] is None:
		return {"scientific_value": None, "discovery_draft": None}

	if state["scientific_value"] == "useless noise":
		logs = list(state["execution_logs"])
		logs.append("Hypothesis assessed as trivial truth; discarded.")
		return {
			"scientific_value": "useless noise",
			"discovery_draft": None,
			"execution_logs": logs,
		}

	discovery = _build_discovery(
		hypothesis=state["hypothesis_draft"],
		evidence=state["collected_evidence"],
		outcome=state["evaluation_outcome"],
	)
	return {"scientific_value": "valuable knowledge", "discovery_draft": discovery}


def request_admission(state: HAState, *, mock_admission_call: AdmissionCall) -> dict[str, Any]:
	if state["discovery_draft"] is None:
		return {}

	admitted = mock_admission_call(state["discovery_draft"])
	if admitted:
		return {}

	logs = list(state["execution_logs"])
	logs.append("Admission Authority rejected the discovery draft.")
	return {"execution_logs": logs, "discovery_draft": None}


def handle_failure_and_logs(state: HAState) -> dict[str, Any]:
	logs = list(state["execution_logs"])
	if state["hypothesis_draft"] is None:
		message = "Task too vague or complex to form a single hypothesis."
	elif not state["de_capability_requests"]:
		message = "No feasible DE request plan could be produced."
	elif not state["collected_evidence"]:
		message = "Data Explorer failed to return intended evidence after replanning."
	elif state["discovery_draft"] is None and state["scientific_value"] == "valuable knowledge":
		message = "Admission Authority rejected the discovery draft."
	else:
		message = "Hypothesis analysis terminated after a recoverable structural failure."

	if message not in logs:
		logs.append(message)

	return {"execution_logs": logs}


def compile_result(state: HAState) -> dict[str, Any]:
	package = _result_package(state)
	succeeded = bool(state["hypothesis_draft"] and state["collected_evidence"])
	result = HypothesisAnalystResult(
		source_role="hypothesis_analyst",
		task_id=state["request"].input.task.task_id,
		work_id=f"ha:{state['request'].input.task.task_id}",
		status=ExecutionStatus.SUCCEEDED if succeeded else ExecutionStatus.FAILED,
		failure=(
			None
			if succeeded
			else ExecutionFailure(
				code="scientific_analysis_incomplete",
				message="Hypothesis Analyst did not complete its donor workflow.",
			)
		),
		hypothesis_draft=package["hypothesis_draft"],
		evidence_drafts=package["evidence_drafts"],
		discovery_draft=state["discovery_draft"],
		evidence_refs=package["evidence_refs"],
		execution_details=package["execution_logs"],
		evaluation_outcome=package["evaluation_outcome"],
		scientific_value=package["scientific_value"],
	)
	return {"final_result": result}

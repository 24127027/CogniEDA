from __future__ import annotations

import pytest
from pydantic import ValidationError

from cognieda.agents.planner.context import PlannerContext
from cognieda.agents.planner.state import PlannerState
from cognieda.agents.planner.types import PlannerOutput, PlannerResult
from cognieda.schemas import (
    Assumption,
    DataProfile,
    Discovery,
    DiscoveryClaim,
    Evidence,
    EvidenceProvenance,
    Hypothesis,
    Objective,
    Task,
    ValidityBasis,
)
from cognieda.schemas.enums import DiscoveryEpistemicStatus, TaskKind
from cognieda.schemas.plan import Plan


def _task(objective: Objective, instruction: str = "Profile missing values.") -> Task:
    return Task(
        objective_id=objective.objective_id,
        kind=TaskKind.DATA,
        instruction=instruction,
    )


def _plan(objective: Objective, tasks: tuple[Task, ...]) -> Plan:
    return Plan(
        objective=objective,
        tasks=tasks,
    )


def _evidence_and_discovery(
    task: Task,
    profile: DataProfile,
) -> tuple[Evidence, Hypothesis, Discovery]:
    evidence = Evidence(
        task_id=task.task_id,
        data_profile_id=profile.data_profile_id,
        content={"missing": 0},
        provenance=EvidenceProvenance(
            producer_role="data_explorer",
            work_reference="work:missingness",
            dataset_reference="dataset:v1",
            data_profile_id=profile.data_profile_id,
        ),
    )
    hypothesis = Hypothesis(
        task_id=task.task_id,
        profile_id=profile.data_profile_id,
        statement="The admitted dataset has no missing values.",
        scope="dataset:v1",
        validation_method="complete count",
        evidence_expectation="one admitted missingness observation",
    )
    discovery = Discovery(
        hypothesis_id=hypothesis.hypothesis_id,
        evidence_ids=[evidence.evidence_id],
        claim=DiscoveryClaim(
            statement="No values were missing in the admitted dataset.",
            scope="dataset:v1",
        ),
        epistemic_status=DiscoveryEpistemicStatus.SUPPORTED,
        scope="dataset:v1",
        validity_basis=ValidityBasis(
            data_profile_id=profile.data_profile_id,
            analysis_frame_refs=["analysis:missingness"],
            hypothesis_id=hypothesis.hypothesis_id,
            evidence_ids=[evidence.evidence_id],
            method="complete count",
            decision_rule="Support when missing count equals zero.",
        ),
    )
    return evidence, hypothesis, discovery


def test_planner_context_and_result_have_exact_canonical_fields() -> None:
    assert tuple(PlannerContext.model_fields) == (
        "active_plans",
        "objectives",
        "assumptions",
        "hypotheses",
        "evidences",
        "discoveries",
        "data_profile",
    )
    assert "active_plan" not in PlannerContext.model_fields
    assert "objective" not in PlannerContext.model_fields
    assert tuple(PlannerResult.model_fields) == (
        "plan",
        "response",
        "human_input_request",
        "continue_execution",
        "discard_candidate",
    )
    assert tuple(PlannerOutput.model_fields) == ("result", "segment", "error")
    assert tuple(PlannerState.__annotations__) == (
        "latest_human_input",
        "candidate_plan",
        "turn_outcome",
        "completed_segments",
    )
    assert "completed_segment" not in PlannerState.__annotations__
    assert "messages" not in PlannerState.__annotations__
    assert "context" not in PlannerState.__annotations__


def test_planner_context_retains_all_typed_readable_state() -> None:
    objective = Objective(text="Understand customer retention.")
    assumption = Assumption(text="Rows represent customers.")
    task = _task(objective)
    profile = DataProfile(row_count=10, column_count=0, columns=())
    evidence, hypothesis, discovery = _evidence_and_discovery(task, profile)
    active_plan = _plan(objective, (task,))

    context = PlannerContext(
        active_plans=(active_plan,),
        objectives=(objective,),
        assumptions=(assumption,),
        hypotheses=(hypothesis,),
        evidences=(evidence,),
        discoveries=(discovery,),
        data_profile=profile,
    )

    assert context.active_plans == (active_plan,)
    assert context.objectives == (objective,)
    assert context.assumptions == (assumption,)
    assert context.hypotheses == (hypothesis,)
    assert context.evidences == (evidence,)
    assert context.discoveries == (discovery,)
    assert context.data_profile is profile
    assert "tasks" not in PlannerContext.model_fields
    assert "conversation_history" not in PlannerContext.model_fields
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PlannerContext(tasks=(task,))  # type: ignore[call-arg]


def test_response_candidate_plan_and_human_input_request_are_valid() -> None:
    objective = Objective(text="Understand customer retention.")
    task = _task(objective)
    plan = _plan(objective, (task,))

    assert PlannerResult(response="The admitted evidence answers this.").plan is None
    candidate = PlannerResult(
        plan=plan,
        response="I propose this bounded investigation.",
    )
    assert candidate.plan is plan
    assert candidate.plan.tasks == (task,)
    assert PlannerResult(human_input_request="Which cohort is in scope?").plan is None


def test_candidate_cannot_be_generated_and_authorized_in_same_result() -> None:
    objective = Objective(text="Understand customer retention.")
    task = _task(objective)

    with pytest.raises(ValidationError, match="candidate Plan"):
        PlannerResult(
            plan=_plan(objective, (task,)),
            continue_execution=True,
        )
    with pytest.raises(ValidationError, match="Human input request"):
        PlannerResult(
            human_input_request="Confirm the cohort.",
            continue_execution=True,
        )


def test_discard_signal_has_exact_structural_conflicts() -> None:
    objective = Objective(text="Understand customer retention.")
    task = _task(objective)
    plan = _plan(objective, (task,))

    assert PlannerResult(discard_candidate=True).discard_candidate is True
    assert (
        PlannerResult(
            response="Discarded the proposal.",
            discard_candidate=True,
        ).response
        == "Discarded the proposal."
    )
    with pytest.raises(ValidationError, match="new candidate Plan"):
        PlannerResult(plan=plan, discard_candidate=True)
    with pytest.raises(ValidationError, match="continue_execution"):
        PlannerResult(continue_execution=True, discard_candidate=True)
    with pytest.raises(ValidationError, match="Human input request"):
        PlannerResult(
            human_input_request="Which proposal?",
            discard_candidate=True,
        )


def test_empty_result_is_rejected() -> None:
    with pytest.raises(ValidationError, match="meaningful conclusion"):
        PlannerResult()


def test_model_visible_contracts_exclude_execution_routing() -> None:
    visible_fields = set(PlannerContext.model_fields) | set(PlannerResult.model_fields)
    result_schema = str(PlannerResult.model_json_schema())

    for forbidden in (
        "Capability",
        "dispatcher",
        "provider",
        "executor",
        "worker",
        "selected_capability",
        "created_assumption",
    ):
        assert forbidden not in visible_fields
        assert forbidden not in result_schema


def _assembled_planner_instruction() -> str:
    from cognieda.agents.planner.agent import Planner

    planner = Planner.__new__(Planner)
    planner._agent_instruction = None
    return " ".join("\n".join(planner._assemble_instructions()).split())


def test_planner_instruction_enforces_read_only_graph_and_no_graph_writes() -> None:
    instruction = _assembled_planner_instruction()

    # A. GRAPH Tasks are read-only semantic graph inquiry
    assert "Graph Miner is strictly READ-ONLY." in instruction
    assert "a GRAPH Task expresses a bounded read-only semantic graph inquiry" in instruction

    # B. Graph Miner cannot write/admit/integrate/persist semantic knowledge
    assert (
        "GRAPH Task MUST NEVER instruct Graph Miner or any component to add nodes, "
        "add edges, integrate findings or discoveries into the graph"
    ) in instruction
    assert (
        "persist Discoveries, admit Discoveries, update semantic knowledge, "
        "modify Objective-Hypothesis relationships, or perform governance"
    ) in instruction

    # C. Planner must not automatically create a final graph-integration Task
    assert (
        "Planner MUST NOT automatically append a final graph-integration or discovery-writing Task"
    ) in instruction
    assert "Integrate validated discoveries into the semantic knowledge graph" in instruction
    assert (
        "Discovery admission and semantic graph mutation belong strictly "
        "to Application and governance authority"
    ) in instruction


def test_planner_instruction_enforces_scientific_task_and_hypothesis_boundaries() -> None:
    instruction = _assembled_planner_instruction()

    # D. Every eligible feasible leaf SCIENTIFIC Task is scoped for exactly one Hypothesis
    assert (
        "Each eligible feasible leaf SCIENTIFIC Task corresponds to exactly one Hypothesis; "
        "infeasible work receives none."
    ) in instruction
    assert (
        "Planner must scope each leaf SCIENTIFIC Task so that Hypothesis Analyst "
        "can formalize exactly ONE scientific proposition from it"
    ) in instruction

    # E. Hypothesis authoring belongs to Hypothesis Analyst, not Planner
    assert (
        "Hypothesis Analyst owns scientific feasibility, hypothesis formalization"
    ) in instruction
    assert ("Planner MUST NOT author Hypothesis statements or evaluate Hypotheses") in instruction

    # F. Independent scientific claims split into separate leaf Tasks
    assert (
        "Planner MUST NOT combine multiple independent claims into one leaf SCIENTIFIC Task"
    ) in instruction
    assert (
        "separate independent claims that can succeed or fail independently into "
        "distinct leaf SCIENTIFIC Tasks"
    ) in instruction
    assert (
        "do not mechanically split variables: a bounded multivariate scientific proposition "
        "representing one coherent claim remains a single SCIENTIFIC Task"
    ) in instruction

    # G. Planner must not select detailed scientific methods, parameters, or rules
    assert "Planner must stay method-agnostic at the scientific protocol level" in instruction
    assert "MUST NOT prescribe specific statistical tests or methods" in instruction
    assert "logistic regression, Pearson correlation, chi-square" in instruction
    assert "significance thresholds (such as p < 0.05)" in instruction
    assert "confidence intervals" in instruction
    assert "seeds, decision rules, holdout splits, or robustness protocols" in instruction
    assert "Protocol and method decisions belong strictly to scientific authority" in instruction


def test_planner_instruction_enforces_data_scope_assumptions_and_tool_boundaries() -> None:
    instruction = _assembled_planner_instruction()

    # H. Planner describes DATA scope semantically without binding exact execution details
    assert "DATA Tasks describe bounded semantic data goals in words" in instruction
    assert (
        "Planner MUST NOT bind exact DataProfile IDs, physical dataset paths or files, "
        "exact column bindings, exact executor capabilities, or analysis implementation details"
    ) in instruction
    assert (
        "Exact DataProfile binding and data resolution belong to Data Explorer "
        "and execution authority"
    ) in instruction

    # I. Assumptions and conversation history are non-empirical
    assert "Assumptions guide planning only;" in instruction
    assert (
        "cannot be treated as Evidence, copied as empirical premises, or used to "
        "claim empirical support or conclude Discoveries"
    ) in instruction
    assert (
        "Conversation history, chat memory, and model-generated possibilities "
        "are non-authoritative and cannot provide empirical support or establish scientific truth"
    ) in instruction

    # J. Planner still must not select capabilities/providers/executors/workers/tools
    assert "Do not select capabilities, providers, executors, workers, or tools." in instruction
    assert "Planner execution and object edit workflows remain deferred." in instruction
    assert "There is no SYNTHESIS Task." in instruction


def test_planner_instruction_enforces_multiple_active_plans_clarification_rule() -> None:
    instruction = _assembled_planner_instruction()

    assert "Inspect the existing Objectives, admitted" in instruction
    assert (
        "Without a retained candidate, it means the currently active authoritative Plan "
        "should continue and is valid only when the typed context contains exactly one active Plan."
    ) in instruction
    assert (
        "If no candidate exists and multiple active Plans are present, "
        "do not return continue_execution; request necessary Human clarification instead."
    ) in instruction

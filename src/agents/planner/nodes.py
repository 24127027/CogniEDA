from uuid import UUID

from langgraph.runtime import Runtime
from pydantic import BaseModel, ValidationError
from sqlmodel import Session

from application.orchestrator.planner_commit import commit_planner_operations
from db.session import get_session
from repositories import (
    DataProfileRepository,
    HypothesisRepository,
    PlannerOperationRepository,
    TaskRepository,
)
from schemas.artifacts import Discovery, Evidence, Hypothesis
from schemas.common import DiscoveryClaim, EvidenceProvenance, ValidityBasis
from schemas.enums import (
    DataProfileLifecycleState,
    DiscoveryEpistemicStatus,
    HypothesisEvidenceOutcome,
    HypothesisStatus,
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskKind,
    TaskLifecycleState,
)
from schemas.planner_operations import PlannerOperation
from schemas.provenance import AnalysisFrame, ExecutionRun

from ..utilities.nodes_registry import NodeRegistry
from .types import (
    COMMAND_TO_INTENT,
    AnalysisFrameObservation,
    Context,
    ExecutionPreparation,
    ExecutionReviewResult,
    ExecutionRunObservation,
    ExecutionSpecification,
    HypothesisDraft,
    PreparedExecution,
    RequestUnderstanding,
    RequestUnderstandingModel,
    State,
    TaskSelection,
    parse_explicit_command,
)

registry = NodeRegistry[State, Context]()
R = registry.R

# --------------------
# Core
# --------------------


class _ConfiguredRequestUnderstandingModel(RequestUnderstandingModel):
    """Adapter over the repository LLM factory for request-only classification."""

    def __init__(self) -> None:
        from agents.llm import ModelConfig, create_agent

        self._agent = create_agent("planner", ModelConfig())

    def understand(self, prompt: str) -> RequestUnderstanding:
        result = self._agent.run_sync(prompt, output_type=RequestUnderstanding)
        return RequestUnderstanding.model_validate(result.output)


def _request_understanding_prompt(query: str) -> str:
    """Build the request-only prompt used for deterministic-stage LLM classification."""

    intent_definitions = "\n".join(
        f"- {intent}: classify requests that should be routed to {intent}."
        for intent in COMMAND_TO_INTENT.values()
    )
    return (
        "Classify only the latest raw user request into one allowed planner intent.\n"
        "Return structured output with `intent` and `request_text`.\n"
        "Do not invent IDs, Assumptions, Evidence, Discoveries, factual project state, "
        "or any other research objects. Do not use prior conversation, SessionFrame, "
        "or retrieved research context.\n"
        "Allowed intents:\n"
        f"{intent_definitions}\n\n"
        f"Latest raw user request:\n{query}"
    )


def _invalid_command_understanding(
    original_command: str,
    request_text: str,
) -> RequestUnderstanding:
    supported_commands = tuple(f"/{command}" for command in COMMAND_TO_INTENT)
    return RequestUnderstanding(
        intent=None,
        request_text=request_text,
        source="invalid_command",
        explicit_command=original_command,
        requires_user_correction=True,
        error_message=(
            f"Unsupported command '{original_command}'. Supported commands: "
            f"{', '.join(supported_commands)}."
        ),
        supported_commands=supported_commands,
    )


def _invalid_llm_understanding(query: str) -> RequestUnderstanding:
    return RequestUnderstanding(
        intent=None,
        request_text=query,
        source="invalid_llm",
        requires_user_correction=True,
        error_message=(
            "Unable to classify the request. Please restate it or use a supported command."
        ),
        supported_commands=tuple(f"/{command}" for command in COMMAND_TO_INTENT),
    )


@registry.register()
def understand_request(state: State, runtime: Runtime[Context]) -> State:
    """
    LLM interprets the user's latest message.

    The model identifies the user's intent and extracts any information
    needed for subsequent planning. This step intentionally does not
    consume Session Frame context so intent recognition is based solely
    on the user's request.
    """
    command = parse_explicit_command(state.query)
    if command is not None:
        intent = COMMAND_TO_INTENT.get(command.command)
        if intent is None:
            state.request_understanding = _invalid_command_understanding(
                command.original_command,
                command.request_text,
            )
        else:
            state.request_understanding = RequestUnderstanding(
                intent=intent,
                request_text=command.request_text,
                source="explicit_command",
                explicit_command=command.command,
            )
        return state

    context = _runtime_context(runtime)
    model = (
        context.request_understanding_model
        if context is not None and context.request_understanding_model is not None
        else _ConfiguredRequestUnderstandingModel()
    )
    try:
        state.request_understanding = RequestUnderstanding.model_validate(
            model.understand(_request_understanding_prompt(state.query))
        )
    except (TypeError, ValueError, ValidationError):
        state.request_understanding = _invalid_llm_understanding(state.query)
    return state


def route_intent(state: State, runtime: Runtime[Context]) -> str:
    """Route the user's intent to the appropriate node and return a routing key."""
    understanding = state.request_understanding
    if (
        understanding is None
        or understanding.requires_user_correction
        or understanding.intent is None
    ):
        return "invalid_request"
    return understanding.intent


@registry.register()
def invalid_request(state: State, runtime: Runtime[Context]) -> State:
    """Terminal controlled route for unsupported or unclassifiable requests."""

    return state


# --------------------
# Question answering
# --------------------


@registry.register()
def answer_question(state: State, runtime: Runtime[Context]) -> None:
    """LLM answers the user's question

    The LLM is provided with context from the session, so it can answer the question more
    accurately.
    """
    pass


# --------------------
# Research planning
# --------------------


@registry.register()
def propose_questions(state: State, runtime: Runtime[Context]) -> None:
    """
    LLM proposes possible research directions, open questions, or
    investigation ideas based on the current research context.
    """
    pass


@registry.register()
def expand_plan(state: State, runtime: Runtime[Context]) -> None:
    """
    LLM expands an approved research direction into executable Tasks.

    This may include refining scope, decomposing large Tasks into
    subtasks, identifying dependencies, and determining a concrete
    execution plan.
    """
    pass


# --------------------
# Task management
# --------------------

@registry.register()
def manage_tasks(state: State, runtime: Runtime[Context]) -> State:
    """
    Draft Task operations without directly mutating persistent Task records.

    Later workflow code can decide which operations require user approval before
    commit applies them.
    """
    session_id = _session_id(state, runtime)
    for task in state.task_create_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CREATE_TASK,
                payload=task.model_dump(mode="json"),
                produced_by_node=PlannerNodeName.MANAGE_TASKS,
            )
        )
    for task_update in state.task_update_payloads:
        parent_task_id = (
            UUID(state.resolve_object_reference(task_update.parent_task_ref))
            if task_update.parent_task_ref is not None
            else None
        )
        profile_id = (
            UUID(state.resolve_object_reference(task_update.data_profile_ref))
            if task_update.data_profile_ref is not None
            else None
        )
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_TASK,
                payload=task_update.operation_payload(
                    task_id=UUID(state.resolve_object_reference(task_update.task_ref)),
                    parent_task_id=parent_task_id,
                    profile_id=profile_id,
                ).model_dump(
                    mode="json",
                    exclude_unset=True,
                ),
                produced_by_node=PlannerNodeName.MANAGE_TASKS,
            )
        )
    for task_state_change in state.task_state_change_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_TASK_STATE,
                payload=task_state_change.operation_payload(
                    task_id=UUID(state.resolve_object_reference(task_state_change.task_ref)),
                ).model_dump(
                    mode="json",
                    exclude_unset=True,
                ),
                produced_by_node=PlannerNodeName.MANAGE_TASKS,
            )
        )
    return state


@registry.register()
def select_task(state: State, runtime: Runtime[Context]) -> State:
    """Resolve an external Task id once, then use only a local reference in the graph."""

    request_text = (
        state.request_understanding.request_text
        if state.request_understanding is not None
        else ""
    )
    if not request_text:
        state.task_selection = TaskSelection(
            error_code="missing_task_reference",
            error_message="/execute requires one exact Task ID.",
        )
        return state

    try:
        task_id = UUID(request_text)
    except ValueError:
        state.task_selection = TaskSelection(
            error_code="malformed_task_reference",
            error_message="/execute requires one exact UUID Task ID.",
        )
        return state

    session = _read_session(runtime)
    if session is None:
        state.task_selection = TaskSelection(
            error_code="execution_store_unavailable",
            error_message="Execution requires a configured planner database.",
        )
        return state
    try:
        task = TaskRepository(session).get_by_id(task_id)
    finally:
        session.close()
    if task is None:
        state.task_selection = TaskSelection(
            error_code="unknown_task_id",
            error_message="The requested Task does not exist.",
        )
        return state

    task_ref = state.bind_object_reference("task", str(task.task_id))
    state.task_selection = TaskSelection(task_ref=task_ref, selected=True)
    return state


# --------------------
# Execution
# --------------------


@registry.register()
def prepare_execution(state: State, runtime: Runtime[Context]) -> State:
    """Compile an admitted Task specification into one transient Hypothesis draft."""

    selection = state.task_selection
    if selection is None or not selection.selected or selection.task_ref is None:
        return _execution_not_prepared(state, "task_not_selected", "No Task was selected.")
    try:
        task_id = UUID(state.resolve_object_reference(selection.task_ref))
    except ValueError:
        return _execution_not_prepared(
            state,
            "unknown_task_reference",
            "The selected local Task reference cannot be resolved.",
        )
    session = _read_session(runtime)
    if session is None:
        return _execution_not_prepared(
            state,
            "execution_store_unavailable",
            "Execution requires a configured planner database.",
        )
    try:
        task_repository = TaskRepository(session)
        task = task_repository.get_by_id(task_id)
        has_children = bool(task_repository.list(parent_task_id=task_id)) if task else False
    finally:
        session.close()
    if task is None:
        return _execution_not_prepared(
            state,
            "unknown_task_reference",
            "The selected Task no longer exists.",
        )
    if task.lifecycle_state != TaskLifecycleState.ACTIVE:
        return _execution_not_prepared(state, "task_not_active", "Task must be active.")
    if task.task_kind != TaskKind.ANALYTICAL:
        return _execution_not_prepared(state, "task_not_analytical", "Task must be analytical.")
    if task.profile_id is None:
        return _execution_not_prepared(
            state, "missing_data_profile", "Task must reference one DataProfile."
        )
    if task.analytical_specification is None:
        return _execution_not_prepared(
            state,
            "missing_analytical_specification",
            "Task requires a structured analytical specification.",
        )
    specification = task.analytical_specification
    if specification.data_profile_id != task.profile_id:
        return _execution_not_prepared(
            state,
            "profile_specification_mismatch",
            "Task and analytical specification must reference the same DataProfile.",
        )

    session = _read_session(runtime)
    if session is None:
        return _execution_not_prepared(
            state,
            "execution_store_unavailable",
            "Execution requires a configured planner database.",
        )
    try:
        profile = DataProfileRepository(session).get_by_id(task.profile_id)
        existing_hypotheses = HypothesisRepository(session).list(task_id=task.task_id)
    finally:
        session.close()
    if has_children:
        return _execution_not_prepared(
            state, "task_has_child_tasks", "Parent Tasks cannot execute analytically."
        )
    if profile is None:
        return _execution_not_prepared(
            state, "unknown_data_profile", "The Task DataProfile does not exist."
        )
    if not (
        profile.lifecycle_state == DataProfileLifecycleState.ACTIVE
        and profile.accepted_as_ground_truth
    ):
        return _execution_not_prepared(
            state, "data_profile_not_accepted", "The Task DataProfile is not accepted and active."
        )
    if not task.variables:
        return _execution_not_prepared(
            state,
            "missing_task_variables",
            "An analytical Task must identify grounded variables or metrics.",
        )
    if not task.evidence_expectation:
        return _execution_not_prepared(
            state,
            "missing_task_evidence_expectation",
            "An analytical Task must define its evidence expectation.",
        )
    unknown_bindings = sorted(
        set(specification.variable_bindings) - set(profile.schema_summary.column_order)
    )
    if unknown_bindings:
        return _execution_not_prepared(
            state,
            "ungrounded_variable_binding",
            "Analytical variable bindings must exist in the accepted DataProfile schema: "
            f"{', '.join(unknown_bindings)}.",
        )
    if not task.can_generate_hypothesis(
        has_child_tasks=has_children,
        data_profile_accepted=True,
    ):
        return _execution_not_prepared(
            state,
            "task_not_execution_ready",
            "The Task does not satisfy the terminal analytical execution contract.",
        )
    if existing_hypotheses:
        return _execution_not_prepared(
            state,
            "hypothesis_already_generated",
            "A Task can generate exactly one Hypothesis.",
        )

    profile_ref = state.bind_object_reference("data_profile", str(profile.profile_id))
    hypothesis = HypothesisDraft(
        statement=specification.hypothesis_statement,
        variables=specification.variable_bindings,
        scope=specification.scope,
        validation_method=specification.validation_method,
        evidence_expectation=specification.evidence_expectation,
    )
    state.prepared_execution = PreparedExecution(
        task_ref=selection.task_ref,
        data_profile_ref=profile_ref,
        task_title=task.title,
        dataset_path=profile.dataset_path,
        hypothesis=hypothesis,
        specification=ExecutionSpecification(
            claim_type=specification.claim_type,
            variable_bindings=specification.variable_bindings,
            scope=specification.scope,
            evidence_expectation=specification.evidence_expectation,
            decision_rule=specification.decision_rule,
            validation_method=specification.validation_method,
            executor_id=specification.executor_id,
            method_parameters=specification.method_parameters,
        ),
        deterministic_seed=specification.deterministic_seed,
    )
    state.execution_preparation = ExecutionPreparation(prepared=True)
    return state


@registry.register()
def dispatch_executor(state: State, runtime: Runtime[Context]) -> State:
    """Invoke the injected deterministic executor once for a prepared execution."""

    prepared = state.prepared_execution
    if state.execution_preparation is None or not state.execution_preparation.prepared:
        return state
    context = _runtime_context(runtime)
    executor = context.analytical_executor if context is not None else None
    if prepared is None or executor is None:
        state.executor_result = None
        return _execution_not_prepared(
            state, "executor_unavailable", "No executor is configured for this execution."
        )
    try:
        state.executor_result = executor.execute(prepared)
    except Exception as exc:  # executor boundary: retain controlled failure only
        state.executor_result = None
        state.execution_review = ExecutionReviewResult(
            error_code="executor_exception",
            error_message=str(exc),
        )
    return state


@registry.register()
def review_execution(state: State, runtime: Runtime[Context]) -> State:
    """Turn typed executor output into ordered PlannerOperations, without persistence."""

    prepared = state.prepared_execution
    result = state.executor_result
    if prepared is None or result is None:
        if state.execution_review is None:
            state.execution_review = ExecutionReviewResult(
                error_code="missing_executor_result",
                error_message="No executor result is available for review.",
            )
        return state

    session_id = _session_id(state, runtime)
    try:
        task_id = UUID(state.resolve_object_reference(prepared.task_ref))
        profile_id = UUID(state.resolve_object_reference(prepared.data_profile_ref))
    except ValueError:
        state.execution_review = ExecutionReviewResult(
            error_code="unknown_execution_reference",
            error_message="The approved execution plan cannot resolve its durable references.",
        )
        return state
    hypothesis = Hypothesis(
        task_id=task_id,
        profile_id=profile_id,
        statement=prepared.hypothesis.statement,
        variables=prepared.hypothesis.variables,
        scope=prepared.hypothesis.scope,
        validation_method=prepared.hypothesis.validation_method,
        evidence_expectation=prepared.hypothesis.evidence_expectation,
    )
    analysis_frame = _materialize_analysis_frame(result.analysis_frame, profile_id)
    execution_run = _materialize_execution_run(
        result.execution_run,
        task_id=task_id,
        hypothesis_id=hypothesis.hypothesis_id,
        analysis_frame_id=analysis_frame.analysis_frame_id,
    )
    operations = [
        _execution_operation(
            session_id,
            PlannerOperationType.CREATE_HYPOTHESIS,
            hypothesis,
            PlannerNodeName.REVIEW_EXECUTION,
        ),
        _execution_operation(
            session_id,
            PlannerOperationType.CREATE_ANALYSIS_FRAME,
            analysis_frame,
            PlannerNodeName.REVIEW_EXECUTION,
        ),
        _execution_operation(
            session_id,
            PlannerOperationType.CREATE_EXECUTION_RUN,
            execution_run,
            PlannerNodeName.REVIEW_EXECUTION,
        ),
    ]
    if result.status == "failed":
        state.planner_operations.extend(operations)
        state.execution_review = ExecutionReviewResult(reviewed=True, succeeded=False)
        return state

    observation = result.evidence_observation
    evaluation = result.evaluation
    if (
        observation is None
        or evaluation is None
    ):
        state.execution_review = ExecutionReviewResult(
            error_code="invalid_completed_result",
            error_message="Completed executor result must evaluate the prepared Hypothesis.",
        )
        return state
    if (
        observation.method != prepared.specification.validation_method
        or result.execution_run.method_id != prepared.specification.validation_method
    ):
        state.execution_review = ExecutionReviewResult(
            error_code="executor_method_mismatch",
            error_message="Executor output method identity must match the prepared specification.",
        )
        return state
    if observation.parameters != prepared.specification.method_parameters:
        state.execution_review = ExecutionReviewResult(
            error_code="executor_parameter_mismatch",
            error_message=(
                "Executor Evidence parameters must match the prepared specification."
            ),
        )
        return state
    evidence = Evidence(
        hypothesis_id=hypothesis.hypothesis_id,
        profile_id=profile_id,
        analysis_frame_ref=str(analysis_frame.analysis_frame_id),
        execution_run_ref=str(execution_run.execution_run_id),
        evidence_type=observation.evidence_type,
        method=observation.method,
        parameters=observation.parameters,
        provenance=EvidenceProvenance(
            analysis_frame_ref=str(analysis_frame.analysis_frame_id),
            execution_run_ref=str(execution_run.execution_run_id),
            code_reference=observation.code_reference,
            environment_reference=observation.environment_reference,
            artifact_paths=observation.artifact_refs,
        ),
        result_summary=observation.result_summary,
        artifact_refs=observation.artifact_refs,
        limitations=observation.limitations,
    )
    discovery = _discovery_from_evaluation(
        hypothesis=hypothesis,
        evidence=evidence,
        analysis_frame_ref=str(analysis_frame.analysis_frame_id),
        decision_rule=prepared.specification.decision_rule,
        evaluation=evaluation.outcome,
        evaluation_note=evaluation.note,
        code_reference=observation.code_reference,
        environment_reference=observation.environment_reference,
    )
    operations.extend(
        [
            _execution_operation(
                session_id,
                PlannerOperationType.CREATE_EVIDENCE,
                evidence,
                PlannerNodeName.REVIEW_EXECUTION,
            ),
            _execution_operation(
                session_id,
                PlannerOperationType.CREATE_DISCOVERY,
                discovery,
                PlannerNodeName.REVIEW_EXECUTION,
            ),
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_HYPOTHESIS_STATE,
                payload={
                    "hypothesis_id": str(hypothesis.hypothesis_id),
                    "status": HypothesisStatus.COMPLETED.value,
                },
                produced_by_node=PlannerNodeName.REVIEW_EXECUTION,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            ),
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_TASK_STATE,
                payload={
                    "task_id": str(task_id),
                    "lifecycle_state": TaskLifecycleState.COMPLETED.value,
                },
                produced_by_node=PlannerNodeName.REVIEW_EXECUTION,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            ),
        ]
    )
    state.planner_operations.extend(operations)
    state.execution_review = ExecutionReviewResult(reviewed=True, succeeded=True)
    return state


# --------------------
# Knowledge management
# --------------------


@registry.register()
def review_conflicts(state: State, runtime: Runtime[Context]) -> State:
    """Draft review flags when Discoveries contradict Assumptions.

    Flagging is a user-review signal; it does not rewrite Assumption truth.
    """
    session_id = _session_id(state, runtime)
    for draft in state.conflict_flag_payloads:
        discovery_id = (
            UUID(state.resolve_object_reference(draft.discovery_ref))
            if draft.discovery_ref is not None
            else None
        )
        contradicted_by_discovery_id = (
            UUID(state.resolve_object_reference(draft.contradicted_by_discovery_ref))
            if draft.contradicted_by_discovery_ref is not None
            else None
        )
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.FLAG_OBJECT,
                payload=draft.operation_payload(
                    assumption_id=UUID(state.resolve_object_reference(draft.assumption_ref)),
                    discovery_id=discovery_id,
                    contradicted_by_discovery_id=contradicted_by_discovery_id,
                ).model_dump(
                    mode="json",
                    exclude_unset=True,
                ),
                produced_by_node=PlannerNodeName.REVIEW_CONFLICTS,
            )
        )
    return state


@registry.register()
def manage_objective(state: State, runtime: Runtime[Context]) -> State:
    """Draft Objective update operations without mutating the Objective directly."""
    session_id = _session_id(state, runtime)
    for draft in state.objective_update_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_OBJECTIVE,
                payload=draft.operation_payload(
                    objective_id=UUID(state.resolve_object_reference(draft.objective_ref)),
                ).model_dump(
                    mode="json",
                    exclude_unset=True,
                ),
                produced_by_node=PlannerNodeName.MANAGE_OBJECTIVE,
            )
        )
    return state


@registry.register()
def manage_assumptions(state: State, runtime: Runtime[Context]) -> State:
    """Draft Assumption operations without using Assumptions as inference premises."""
    session_id = _session_id(state, runtime)
    for assumption in state.assumption_create_payloads:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CREATE_ASSUMPTION,
                payload=assumption.model_dump(mode="json"),
                produced_by_node=PlannerNodeName.MANAGE_ASSUMPTIONS,
            )
        )
    for draft in state.assumption_state_update_payloads:
        contradicted_by_discovery_ids = (
            [
                UUID(state.resolve_object_reference(discovery_ref))
                for discovery_ref in draft.contradicted_by_discovery_refs
            ]
            if draft.contradicted_by_discovery_refs is not None
            else None
        )
        replacement_assumption_id = (
            UUID(state.resolve_object_reference(draft.replacement_assumption_ref))
            if draft.replacement_assumption_ref is not None
            else None
        )
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_ASSUMPTION_STATE,
                payload=draft.operation_payload(
                    assumption_id=UUID(state.resolve_object_reference(draft.assumption_ref)),
                    contradicted_by_discovery_ids=contradicted_by_discovery_ids,
                    replacement_assumption_id=replacement_assumption_id,
                ).model_dump(
                    mode="json",
                    exclude_unset=True,
                ),
                produced_by_node=PlannerNodeName.MANAGE_ASSUMPTIONS,
            )
        )
    return state


# --------------------
# User interaction
# --------------------


@registry.register()
def request_user_input(state: State, runtime: Runtime[Context]) -> State:
    """Prepare a request for clarification or other user input."""

    return state


@registry.register()
def pause(state: State, runtime: Runtime[Context]) -> State:
    """Pause the current process and wait for user input or confirmation."""

    return state


@registry.register()
def process_decision(state: State, runtime: Runtime[Context]) -> str:
    """Interpret a future user response and return its planner routing key."""

    raise NotImplementedError(
        "process_decision must return one of: clarify, approved_questions, "
        "approved_task, approved_plan, approved_conflict, approved_execution, cancel."
    )


# --------------------
# Finalization
# --------------------


@registry.register()
def commit(state: State, runtime: Runtime[Context]) -> State:
    """
    Persist approved planner operations at the commit boundary.

    Future work will make approval, transaction, and rollback behavior explicit
    here. Planner nodes must keep producing operations rather than mutating FCOs.
    """
    context = _runtime_context(runtime)
    if context is None or context.database_url is None:
        return state

    session = get_session(context.database_url)
    try:
        _persist_planner_operations(session, state.planner_operations)
        if state.operation_ids_to_commit is not None:
            operation_ids = [UUID(operation_id) for operation_id in state.operation_ids_to_commit]
            state.commit_result = commit_planner_operations(
                session,
                session_id=context.session_id or state.session_id,
                operation_ids=operation_ids,
            )
        else:
            state.commit_result = commit_planner_operations(
                session,
                operations=state.planner_operations,
                session_id=context.session_id or state.session_id,
            )
    finally:
        session.close()
    return state


def _runtime_context(runtime: Runtime[Context] | None) -> Context | None:
    return getattr(runtime, "context", None)


def _read_session(runtime: Runtime[Context] | None) -> Session | None:
    """Open a short-lived read session only when planner execution is configured."""

    context = _runtime_context(runtime)
    if context is None or context.database_url is None:
        return None
    return get_session(context.database_url)


def _execution_not_prepared(
    state: State,
    error_code: str,
    error_message: str,
) -> State:
    state.execution_preparation = ExecutionPreparation(
        prepared=False,
        error_code=error_code,
        error_message=error_message,
    )
    return state


def _materialize_analysis_frame(
    observation: AnalysisFrameObservation,
    profile_id: UUID,
) -> AnalysisFrame:
    """Create immutable provenance only when executor output crosses into commit work."""

    return AnalysisFrame(
        data_profile_id=profile_id,
        frame_hash=observation.frame_hash,
        frame_ref=observation.frame_ref,
        column_refs=observation.column_refs,
        row_filter_description=observation.row_filter_description,
    )


def _materialize_execution_run(
    observation: ExecutionRunObservation,
    *,
    task_id: UUID,
    hypothesis_id: UUID,
    analysis_frame_id: UUID,
) -> ExecutionRun:
    """Create immutable run provenance only at the durable operation boundary."""

    return ExecutionRun(
        task_id=task_id,
        hypothesis_id=hypothesis_id,
        analysis_frame_id=analysis_frame_id,
        executor_type=observation.executor_type,
        method_id=observation.method_id,
        parameter_hash=observation.parameter_hash,
        status=observation.status,
    )


def _execution_operation(
    session_id: str | None,
    operation_type: PlannerOperationType,
    payload: BaseModel,
    produced_by_node: PlannerNodeName,
) -> PlannerOperation:
    """Serialize a typed draft only at the PlannerOperation persistence boundary."""

    return PlannerOperation(
        session_id=session_id,
        operation_type=operation_type,
        payload=payload.model_dump(mode="json"),
        produced_by_node=produced_by_node,
        approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
    )


def _discovery_from_evaluation(
    *,
    hypothesis: Hypothesis,
    evidence: Evidence,
    analysis_frame_ref: str,
    decision_rule: str,
    evaluation: HypothesisEvidenceOutcome,
    evaluation_note: str | None,
    code_reference: str | None,
    environment_reference: str | None,
) -> Discovery:
    """Produce a bounded Discovery without interpreting free text or Assumptions."""

    status, statement = _discovery_conclusion(hypothesis, evaluation)
    return Discovery(
        hypothesis_id=hypothesis.hypothesis_id,
        evidence_ids=[evidence.evidence_id],
        claim=DiscoveryClaim(
            statement=statement,
            scope=hypothesis.scope,
            result=evaluation.value,
        ),
        epistemic_status=status,
        scope=hypothesis.scope,
        validity_basis=ValidityBasis(
            data_profile_id=hypothesis.profile_id,
            analysis_frame_refs=[analysis_frame_ref],
            hypothesis_id=hypothesis.hypothesis_id,
            evidence_ids=[evidence.evidence_id],
            method=evidence.method,
            parameters=evidence.parameters,
            code_reference=code_reference,
            environment_reference=environment_reference,
            decision_rule=decision_rule,
            strength=evaluation.value,
            uncertainty=evaluation_note,
            assumptions_excluded_from_inference=True,
            invalidators=["DataProfile, method, parameter, code, or environment change."],
        ),
    )


def _discovery_conclusion(
    hypothesis: Hypothesis,
    evaluation: HypothesisEvidenceOutcome,
) -> tuple[DiscoveryEpistemicStatus, str]:
    if evaluation == HypothesisEvidenceOutcome.SUPPORTS:
        return DiscoveryEpistemicStatus.SUPPORTED, hypothesis.statement
    if evaluation == HypothesisEvidenceOutcome.CONTRADICTS:
        return (
            DiscoveryEpistemicStatus.CONTRADICTED,
            "Available evidence contradicts the stated hypothesis within scope "
            f"{hypothesis.scope}.",
        )
    if evaluation == HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE:
        return (
            DiscoveryEpistemicStatus.INSUFFICIENT_EVIDENCE,
            "Available evidence is insufficient to evaluate the stated hypothesis "
            f"within scope {hypothesis.scope}.",
        )
    return (
        DiscoveryEpistemicStatus.INCONCLUSIVE,
        "Available evidence is inconclusive for the stated hypothesis within scope "
        f"{hypothesis.scope}.",
    )


def _session_id(state: State, runtime: Runtime[Context] | None) -> str | None:
    context = _runtime_context(runtime)
    if context is not None and context.session_id is not None:
        return context.session_id
    return state.session_id


def _persist_planner_operations(
    session: Session,
    operations: list[PlannerOperation],
) -> None:
    repository = PlannerOperationRepository(session)
    for operation in operations:
        if repository.get_by_id(operation.operation_id) is None:
            repository.create(operation)

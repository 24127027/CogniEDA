import json
from hashlib import sha256
from typing import Any
from uuid import UUID, uuid4

from langgraph.runtime import Runtime
from pydantic import BaseModel, ValidationError
from sqlmodel import Session

from application.orchestrator.planner_commit import commit_planner_operations
from db.models import ExecutionApprovalRecord
from db.session import get_session
from memory.session_frame import SessionFrameBuilder
from repositories import (
    DataProfileRepository,
    DiscoveryRepository,
    EvidenceRepository,
    ExecutionApprovalRepository,
    HypothesisRepository,
    PlannerOperationRepository,
    TaskRepository,
)
from schemas.artifacts import Discovery, EvaluationThresholds, Evidence, Hypothesis, SessionFrame
from schemas.common import DiscoveryClaim, EvidenceProvenance, ValidityBasis
from schemas.enums import (
    DataProfileLifecycleState,
    DiscoveryEpistemicStatus,
    ExecutionApprovalStatus,
    ExecutionRunStatus,
    HypothesisEvidenceOutcome,
    HypothesisStatus,
    PlannerNodeName,
    PlannerOperationApprovalState,
    PlannerOperationType,
    TaskKind,
    TaskLifecycleState,
)
from schemas.planner_operations import PlannerOperation
from schemas.provenance import (
    AnalysisFrame,
    ExecutionApproval,
    ExecutionInbox,
    ExecutionOutbox,
    ExecutionRun,
)

from ..utilities.nodes_registry import NodeRegistry
from .types import (
    COMMAND_TO_INTENT,
    AnalysisFrameObservation,
    Context,
    ContextualGrounding,
    ControlledPlannerError,
    EvidenceAdmission,
    ExecutionAdmission,
    ExecutionPreparation,
    ExecutionRevalidation,
    ExecutionReviewResult,
    ExecutionRunObservation,
    ExecutionSpecification,
    HypothesisDraft,
    HypothesisEvaluation,
    PendingUserInteraction,
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
    if understanding.intent == "answer":
        return "check_answerability"
    return understanding.intent


def route_entry(state: State, runtime: Runtime[Context]) -> str:
    """Resume only through a durable approval identifier when one is supplied."""

    return "resume_execution" if state.resume_approval_id is not None else "understand_request"


@registry.register()
def contextual_grounding(state: State, runtime: Runtime[Context]) -> State:
    """Resolve relative references using SessionFrame."""
    if state.request_understanding is None:
        return state
    state.contextual_grounding = ContextualGrounding(
        resolved_query=state.request_understanding.request_text,
    )
    return state


@registry.register()
def check_answerability(state: State, runtime: Runtime[Context]) -> State:
    """Gate: determine if we have adequate valid basis to answer a question."""
    return state


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
        state.request_understanding.request_text if state.request_understanding is not None else ""
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
        existing_discovery_hypothesis_ids = {
            discovery.hypothesis_id for discovery in DiscoveryRepository(session).list()
        }
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
    existing_hypothesis = existing_hypotheses[0] if len(existing_hypotheses) == 1 else None
    if len(existing_hypotheses) > 1:
        return _execution_not_prepared(
            state,
            "multiple_hypotheses_for_task",
            "A Task has more than one Hypothesis and requires recovery review.",
        )
    if existing_hypothesis is not None:
        if existing_hypothesis.hypothesis_id in existing_discovery_hypothesis_ids:
            return _execution_not_prepared(
                state,
                "hypothesis_already_finalized",
                "The Task Hypothesis already has a final Discovery.",
            )
        if existing_hypothesis.status in {
            HypothesisStatus.CONFIRMED,
            HypothesisStatus.CONTRADICTED,
            HypothesisStatus.INCONCLUSIVE,
            HypothesisStatus.INSUFFICIENT_EVIDENCE,
            HypothesisStatus.CANCELLED,
            HypothesisStatus.ARCHIVED,
        }:
            return _execution_not_prepared(
                state,
                "hypothesis_not_retryable",
                "The Task Hypothesis is terminal and cannot be dispatched again.",
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
        hypothesis_ref=(
            state.bind_object_reference("hypothesis", str(existing_hypothesis.hypothesis_id))
            if existing_hypothesis is not None
            else None
        ),
        contract_fingerprint=_execution_contract_fingerprint(task, profile, specification),
    )
    state.execution_preparation = ExecutionPreparation(prepared=True)
    return state


@registry.register()
def commit_execution_contract(state: State, runtime: Runtime[Context]) -> State:
    """Atomically persist Hypothesis and ExecutionRun before dispatch."""
    session_id = _session_id(state, runtime)
    prepared = state.prepared_execution
    if prepared is None or state.execution_revalidation is None:
        return state
    if not state.execution_revalidation.valid:
        state.hard_stop_code = state.execution_revalidation.error_code or "execution_not_authorized"
        state.hard_stop_message = (
            state.execution_revalidation.error_message
            or "The execution contract has not been approved."
        )
        return state

    try:
        task_id = UUID(state.resolve_object_reference(prepared.task_ref))
        profile_id = UUID(state.resolve_object_reference(prepared.data_profile_ref))
    except ValueError as exc:
        state.hard_stop_code = "unknown_execution_reference"
        state.hard_stop_message = str(exc)
        return state

    context = _runtime_context(runtime)
    if context is None or context.database_url is None:
        state.hard_stop_code = "execution_store_unavailable"
        state.hard_stop_message = "Execution requires a configured planner database."
        return state

    session = get_session(context.database_url)
    try:
        approval_id_text = (
            state.pending_interaction.payload.get("execution_approval_id")
            if state.pending_interaction is not None
            else None
        )
        approval_id = UUID(str(approval_id_text))
        approval_record = session.get(ExecutionApprovalRecord, approval_id)
        if (
            approval_record is None
            or approval_record.session_id != (session_id or "default")
            or approval_record.status != ExecutionApprovalStatus.APPROVED
            or approval_record.contract_fingerprint != prepared.contract_fingerprint
            or approval_record.task_id != task_id
            or approval_record.profile_id != profile_id
        ):
            raise ValueError("The execution approval is stale or has already been consumed.")
        task = TaskRepository(session).get_by_id(task_id)
        profile = DataProfileRepository(session).get_by_id(profile_id)
        if task is None or profile is None:
            raise ValueError("Task or DataProfile missing during revalidation.")
        if (
            task.lifecycle_state != TaskLifecycleState.ACTIVE
            or task.task_kind != TaskKind.ANALYTICAL
            or task.profile_id != profile_id
            or task.analytical_specification is None
            or not profile.accepted_as_ground_truth
            or profile.lifecycle_state != DataProfileLifecycleState.ACTIVE
        ):
            raise ValueError("The persisted Task or DataProfile is no longer execution-ready.")
        current_fingerprint = _execution_contract_fingerprint(task, profile, prepared.specification)
        if current_fingerprint != prepared.contract_fingerprint:
            raise ValueError("The execution contract is stale (underlying data changed).")

        hypothesis: Hypothesis
        if prepared.hypothesis_ref is None:
            hypothesis = Hypothesis(
                task_id=task_id,
                profile_id=profile_id,
                statement=prepared.hypothesis.statement,
                variables=prepared.hypothesis.variables,
                scope=prepared.hypothesis.scope,
                validation_method=prepared.hypothesis.validation_method,
                evidence_expectation=prepared.hypothesis.evidence_expectation,
                status=HypothesisStatus.TESTING,
            )
            hypothesis_operation = _execution_operation(
                session_id,
                PlannerOperationType.CREATE_HYPOTHESIS,
                hypothesis,
                PlannerNodeName.PREPARE_EXECUTION,
            )
        else:
            hypothesis_id = UUID(state.resolve_object_reference(prepared.hypothesis_ref))
            hypothesis = HypothesisRepository(session).get_by_id(hypothesis_id)
            if hypothesis is None:
                raise ValueError("Approved execution references a missing Hypothesis.")
            hypothesis_operation = PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_HYPOTHESIS_STATE,
                payload={
                    "hypothesis_id": str(hypothesis.hypothesis_id),
                    "status": HypothesisStatus.TESTING.value,
                },
                produced_by_node=PlannerNodeName.PREPARE_EXECUTION,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            )

        dispatch_key = str(uuid4())
        execution_run = ExecutionRun(
            task_id=task_id,
            hypothesis_id=hypothesis.hypothesis_id,
            executor_type=prepared.specification.executor_id,
            method_id=prepared.specification.validation_method,
            parameter_hash=_method_parameter_hash(prepared.specification.method_parameters),
            status=ExecutionRunStatus.ADMITTED,
            dispatch_idempotency_key=dispatch_key,
        )

        outbox = ExecutionOutbox(
            execution_run_id=execution_run.execution_run_id,
            dispatch_idempotency_key=dispatch_key,
            executor_type=prepared.specification.executor_id,
            method_id=prepared.specification.validation_method,
            parameter_hash=execution_run.parameter_hash or "",
            prepared_payload=prepared.model_dump(mode="json"),
        )

        approval_record.status = ExecutionApprovalStatus.CONSUMED
        session.add(approval_record)
        operations = [
            operation
            for operation in (
                hypothesis_operation,
                _execution_operation(
                    session_id,
                    PlannerOperationType.CREATE_EXECUTION_RUN,
                    execution_run,
                    PlannerNodeName.PREPARE_EXECUTION,
                ),
                _execution_operation(
                    session_id,
                    PlannerOperationType.CREATE_EXECUTION_OUTBOX,
                    outbox,
                    PlannerNodeName.PREPARE_EXECUTION,
                ),
            )
            if operation is not None
        ]
        _persist_planner_operations(session, operations)
        result = commit_planner_operations(session, session_id=session_id, operations=operations)
        if result.failed_operation_ids:
            state.hard_stop_code = "execution_contract_commit_failed"
            state.hard_stop_message = "; ".join(result.errors.values())
            return state
        state.planner_operations.extend(operations)
        prepared.hypothesis_ref = state.bind_object_reference(
            "hypothesis", str(hypothesis.hypothesis_id)
        )
        prepared.execution_run_ref = state.bind_object_reference(
            "execution_run", str(execution_run.execution_run_id)
        )
        state.execution_admission = ExecutionAdmission(
            admitted=True,
            hypothesis_ref=prepared.hypothesis_ref,
            execution_run_ref=prepared.execution_run_ref,
        )
    except Exception as exc:
        session.rollback()
        state.hard_stop_code = "stale_execution_approval"
        state.hard_stop_message = str(exc)
        state.controlled_error = ControlledPlannerError(
            code=state.hard_stop_code,
            message=state.hard_stop_message,
        )
    finally:
        session.close()
    return state


@registry.register()
def dispatch_executor(state: State, runtime: Runtime[Context]) -> State:
    """Retired Planner-side dispatch node.

    Production terminates after durable admission.  Keeping this node
    side-effect free prevents a direct graph invocation from reintroducing a
    graph-local executor call; only the independent dispatcher consumes an
    admitted outbox record.
    """

    if state.execution_admission is not None and state.execution_admission.admitted:
        state.response_text = "Execution admitted and awaiting durable dispatch."
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
        profile_id = UUID(state.resolve_object_reference(prepared.data_profile_ref))
        execution_run_id = UUID(state.resolve_object_reference(prepared.execution_run_ref))
        hypothesis_id = UUID(state.resolve_object_reference(prepared.hypothesis_ref))
    except ValueError:
        state.execution_review = ExecutionReviewResult(
            error_code="unknown_execution_reference",
            error_message="The approved execution plan cannot resolve its durable references.",
        )
        return state

    analysis_frame = _materialize_analysis_frame(result.analysis_frame, profile_id)
    state.planner_operations.append(
        _execution_operation(
            session_id,
            PlannerOperationType.CREATE_ANALYSIS_FRAME,
            analysis_frame,
            PlannerNodeName.REVIEW_EXECUTION,
        )
    )

    # Store frame ref for later steps
    state.bind_object_reference("analysis_frame", str(analysis_frame.analysis_frame_id))

    if result.status == "failed":
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_EXECUTION_RUN,
                payload={
                    "execution_run_id": str(execution_run_id),
                    "status": "execution_failed",
                },
                produced_by_node=PlannerNodeName.REVIEW_EXECUTION,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            )
        )
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_HYPOTHESIS_STATE,
                payload={
                    "hypothesis_id": str(hypothesis_id),
                    "status": HypothesisStatus.APPROVED.value,
                },
                produced_by_node=PlannerNodeName.REVIEW_EXECUTION,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            )
        )
        state.execution_review = ExecutionReviewResult(reviewed=True, succeeded=False)
    else:
        state.execution_review = ExecutionReviewResult(reviewed=True, succeeded=True)

    lease_epoch = state.resume_payload.get("lease_epoch") if state.resume_payload else None
    dispatch_key = None
    session = _read_session(runtime)
    if session:
        try:
            from db.models import ExecutionRunRecord
            record = session.get(ExecutionRunRecord, execution_run_id)
            if record:
                if lease_epoch is None:
                    lease_epoch = record.lease_epoch
                dispatch_key = record.dispatch_idempotency_key
        finally:
            session.close()

    inbox = ExecutionInbox(
        execution_run_id=execution_run_id,
        dispatch_idempotency_key=dispatch_key or str(uuid4()),
        lease_epoch=lease_epoch or 0,
        result_digest=sha256(result.model_dump_json().encode()).hexdigest(),
        executor_status=result.status,
        serialized_observations=result.model_dump(mode="json"),
        method_id=prepared.specification.validation_method,
    )

    state.planner_operations.append(
        _execution_operation(
            session_id,
            PlannerOperationType.CREATE_EXECUTION_INBOX,
            inbox,
            PlannerNodeName.REVIEW_EXECUTION,
        )
    )

    return state


@registry.register()
def validate_evidence(state: State, runtime: Runtime[Context]) -> State:
    """Structurally validate the raw observation against the durable Hypothesis contract."""
    result = state.executor_result
    prepared = state.prepared_execution
    if result is None or prepared is None or result.status == "failed":
        return state

    observation = result.evidence_observation
    if observation is None:
        state.evidence_admission = EvidenceAdmission(admitted=False, error_message="No evidence")
        return state

    if (
        observation.method != prepared.specification.validation_method
        or result.execution_run.method_id != prepared.specification.validation_method
    ):
        state.evidence_admission = EvidenceAdmission(
            admitted=False, error_message="Method mismatch"
        )
        state.execution_review = ExecutionReviewResult(
            reviewed=True,
            succeeded=False,
            error_code="executor_method_mismatch",
            error_message="Method mismatch",
        )
        _append_execution_failure(state, runtime)
        return state

    if observation.parameters != prepared.specification.method_parameters:
        state.evidence_admission = EvidenceAdmission(
            admitted=False, error_message="Parameter mismatch"
        )
        state.execution_review = ExecutionReviewResult(
            reviewed=True,
            succeeded=False,
            error_code="executor_parameter_mismatch",
            error_message="Parameter mismatch",
        )
        _append_execution_failure(state, runtime)
        return state
    if result.analysis_frame.column_refs != prepared.specification.variable_bindings:
        state.evidence_admission = EvidenceAdmission(
            admitted=False, error_message="Variable binding mismatch"
        )
        state.execution_review = ExecutionReviewResult(
            reviewed=True,
            succeeded=False,
            error_code="executor_variable_binding_mismatch",
            error_message="Executor frame variables must match the prepared specification.",
        )
        _append_execution_failure(state, runtime)
        return state
    if result.execution_run.parameter_hash != _method_parameter_hash(
        prepared.specification.method_parameters
    ):
        state.evidence_admission = EvidenceAdmission(
            admitted=False, error_message="Parameter hash mismatch"
        )
        state.execution_review = ExecutionReviewResult(
            reviewed=True,
            succeeded=False,
            error_code="executor_parameter_hash_mismatch",
            error_message="Executor parameter hash must match the prepared specification.",
        )
        _append_execution_failure(state, runtime)
        return state

    session_id = _session_id(state, runtime)
    try:
        profile_id = UUID(state.resolve_object_reference(prepared.data_profile_ref))
        hypothesis_id = UUID(state.resolve_object_reference(prepared.hypothesis_ref))
        execution_run_id = UUID(state.resolve_object_reference(prepared.execution_run_ref))
    except ValueError as exc:
        state.evidence_admission = EvidenceAdmission(admitted=False, error_message=str(exc))
        return state

    frame_operations = [
        operation
        for operation in state.planner_operations
        if operation.operation_type == PlannerOperationType.CREATE_ANALYSIS_FRAME
    ]
    if len(frame_operations) != 1:
        state.evidence_admission = EvidenceAdmission(
            admitted=False,
            error_message="Evidence admission requires exactly one materialized AnalysisFrame.",
        )
        return state
    analysis_frame_id = frame_operations[0].payload["analysis_frame_id"]

    evidence = Evidence(
        hypothesis_id=hypothesis_id,
        profile_id=profile_id,
        analysis_frame_ref=analysis_frame_id,
        execution_run_ref=str(execution_run_id),
        evidence_type=observation.evidence_type,
        method=observation.method,
        parameters=observation.parameters,
        provenance=EvidenceProvenance(
            analysis_frame_ref=analysis_frame_id,
            execution_run_ref=str(execution_run_id),
            code_reference=observation.code_reference,
            environment_reference=observation.environment_reference,
            artifact_paths=observation.artifact_refs,
        ),
        result_summary=observation.result_summary,
        artifact_refs=observation.artifact_refs,
        limitations=observation.limitations,
    )
    state.planner_operations.append(
        _execution_operation(
            session_id,
            PlannerOperationType.CREATE_EVIDENCE,
            evidence,
            PlannerNodeName.VALIDATE_EVIDENCE,
        )
    )
    state.planner_operations.append(
        PlannerOperation(
            session_id=session_id,
            operation_type=PlannerOperationType.UPDATE_EXECUTION_RUN,
            payload={"execution_run_id": str(execution_run_id), "status": "completed"},
            produced_by_node=PlannerNodeName.VALIDATE_EVIDENCE,
            approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
        )
    )
    evidence_ref = state.bind_object_reference("evidence", str(evidence.evidence_id))
    state.evidence_admission = EvidenceAdmission(admitted=True, evidence_ref=evidence_ref)
    return state


@registry.register()
def evaluate_hypothesis(state: State, runtime: Runtime[Context]) -> State:
    """Review all admitted Evidence for the active Hypothesis. Apply decision rules."""
    result = state.executor_result
    prepared = state.prepared_execution
    if (
        result is None
        or prepared is None
        or result.status == "failed"
        or state.evidence_admission is None
        or not state.evidence_admission.admitted
    ):
        return state
    evaluation = result.evaluation
    if evaluation is None:
        return state
    session_id = _session_id(state, runtime)
    try:
        hypothesis_id = UUID(state.resolve_object_reference(prepared.hypothesis_ref))
        task_id = UUID(state.resolve_object_reference(prepared.task_ref))
        evidence_id = UUID(state.resolve_object_reference(state.evidence_admission.evidence_ref))
    except ValueError as exc:
        state.execution_review = ExecutionReviewResult(
            reviewed=True,
            succeeded=False,
            error_code="unknown_evidence_reference",
            error_message=str(exc),
        )
        return state

    evidence_operation = next(
        (
            operation
            for operation in state.planner_operations
            if operation.operation_type == PlannerOperationType.CREATE_EVIDENCE
            and operation.payload.get("evidence_id") == str(evidence_id)
        ),
        None,
    )
    frame_operation = next(
        (
            operation
            for operation in state.planner_operations
            if operation.operation_type == PlannerOperationType.CREATE_ANALYSIS_FRAME
        ),
        None,
    )
    if evidence_operation is None or frame_operation is None:
        return state

    current_evidence = Evidence(**evidence_operation.payload)
    analysis_frame_id = frame_operation.payload["analysis_frame_id"]
    context = _runtime_context(runtime)
    if context is None or context.database_url is None:
        return state
    session = get_session(context.database_url)
    try:
        hypothesis = HypothesisRepository(session).get_by_id(hypothesis_id)
        admitted_evidence = EvidenceRepository(session).list_for_hypothesis(hypothesis_id)
        task = TaskRepository(session).get_by_id(task_id)
        profile = (
            DataProfileRepository(session).get_by_id(hypothesis.profile_id)
            if hypothesis
            else None
        )
    finally:
        session.close()
    if hypothesis is None or task is None or profile is None:
        return state

    if not evaluation.finalize:
        state.planner_operations.append(
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_HYPOTHESIS_STATE,
                payload={
                    "hypothesis_id": str(hypothesis_id),
                    "status": HypothesisStatus.AWAITING_ADDITIONAL_EVIDENCE.value,
                },
                produced_by_node=PlannerNodeName.EVALUATE_HYPOTHESIS,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            )
        )
        state.hypothesis_evaluation = HypothesisEvaluation(
            evaluated=False,
            new_status=HypothesisStatus.AWAITING_ADDITIONAL_EVIDENCE,
        )
        return state

    computed_outcome = _evaluate_deterministically(
        current_evidence,
        prepared.specification.decision_rule,
        validation_method=prepared.specification.validation_method,
    )
    if evaluation.outcome != computed_outcome:
        state.execution_review = ExecutionReviewResult(
            reviewed=True,
            succeeded=False,
            error_code="evaluation_mismatch",
            error_message=(
                f"Executor advisory outcome ({evaluation.outcome}) contradicts "
                f"deterministic evaluation ({computed_outcome})."
            ),
        )
        run_id = state.resolve_object_reference(prepared.execution_run_ref)
        state.planner_operations = [
            operation
            for operation in state.planner_operations
            if not (
                operation.operation_type == PlannerOperationType.CREATE_EVIDENCE
                and operation.payload.get("evidence_id") == str(evidence_id)
            )
            and not (
                operation.operation_type == PlannerOperationType.UPDATE_EXECUTION_RUN
                and operation.payload.get("execution_run_id") == run_id
            )
        ]
        _append_execution_failure(state, runtime)
        return state

    observation = result.evidence_observation
    discovery = _discovery_from_evaluation(
        hypothesis=hypothesis,
        evidence=current_evidence,
        analysis_frame_ref=analysis_frame_id,
        decision_rule=prepared.specification.decision_rule,
        evaluation=computed_outcome,
        evaluation_note=evaluation.note,
        code_reference=observation.code_reference,
        environment_reference=observation.environment_reference,
    )
    evidence_ids = [
        *(evidence.evidence_id for evidence in admitted_evidence),
        current_evidence.evidence_id,
    ]
    discovery = discovery.model_copy(
        update={
            "evidence_ids": evidence_ids,
            "validity_basis": discovery.validity_basis.model_copy(
                update={"evidence_ids": evidence_ids}
            ),
        }
    )
    status_by_outcome = {
        HypothesisEvidenceOutcome.SUPPORTS: HypothesisStatus.CONFIRMED,
        HypothesisEvidenceOutcome.CONTRADICTS: HypothesisStatus.CONTRADICTED,
        HypothesisEvidenceOutcome.INCONCLUSIVE: HypothesisStatus.INCONCLUSIVE,
        HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE: HypothesisStatus.INSUFFICIENT_EVIDENCE,
    }
    final_status = status_by_outcome[computed_outcome]
    completed_task = task.model_copy(update={"lifecycle_state": TaskLifecycleState.COMPLETED})
    frame = SessionFrame(
        frame_topic="Execution Result",
        objective_snapshot="Ad-hoc execution",
        frame_outcome=discovery.claim.statement,
        data_profile_summaries=[SessionFrameBuilder._profile_summary(profile)],
        active_data_profile_refs=[profile.profile_id],
        # A completed Task/Hypothesis is kept as an auditable reference but
        # omitted from active planning summaries by its lifecycle policy.
        active_task_refs=[completed_task.task_id],
        relevant_discoveries=[SessionFrameBuilder._discovery_summary(discovery)],
        relevant_discovery_refs=[discovery.discovery_id],
        supporting_evidence=[SessionFrameBuilder._evidence_summary(current_evidence)],
        supporting_evidence_refs=[current_evidence.evidence_id],
        inclusion_reasons={
            str(profile.profile_id): "accepted DataProfile for the completed execution",
            str(completed_task.task_id): "completed analytical Task audit reference",
            str(discovery.discovery_id): "new evidence-bound Discovery",
            str(current_evidence.evidence_id): "admitted Evidence for the new Discovery",
        },
        key_warnings=[
            "Assumptions are excluded from execution-result conclusion context.",
            "Completed Task and Hypothesis summaries are not active planning context.",
        ],
    )
    state.planner_operations.extend(
        [
            _execution_operation(
                session_id,
                PlannerOperationType.CREATE_DISCOVERY,
                discovery,
                PlannerNodeName.EVALUATE_HYPOTHESIS,
            ),
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_HYPOTHESIS_STATE,
                payload={
                    "hypothesis_id": str(hypothesis_id),
                    "status": final_status.value,
                },
                produced_by_node=PlannerNodeName.EVALUATE_HYPOTHESIS,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            ),
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_TASK_STATE,
                payload={
                    "task_id": str(task_id),
                    "lifecycle_state": TaskLifecycleState.COMPLETED.value,
                },
                produced_by_node=PlannerNodeName.EVALUATE_HYPOTHESIS,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            ),
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_SESSION_FRAME,
                payload=frame.model_dump(mode="json"),
                produced_by_node=PlannerNodeName.EVALUATE_HYPOTHESIS,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            ),
        ]
    )

    state.hypothesis_evaluation = HypothesisEvaluation(
        evaluated=True,
        new_status=final_status,
    )
    return state


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
    """Durably persist the approval request before exposing it to a caller."""
    prepared = state.prepared_execution
    if (
        prepared is not None
        and state.execution_preparation is not None
        and state.execution_preparation.prepared
    ):
        context = _runtime_context(runtime)
        if context is None or context.database_url is None:
            state.controlled_error = ControlledPlannerError(
                code="execution_store_unavailable",
                message="Execution approval requires a configured planner database.",
            )
            return state
        try:
            task_id = UUID(state.resolve_object_reference(prepared.task_ref))
            profile_id = UUID(state.resolve_object_reference(prepared.data_profile_ref))
            hypothesis_id = (
                UUID(state.resolve_object_reference(prepared.hypothesis_ref))
                if prepared.hypothesis_ref is not None
                else None
            )
        except ValueError as exc:
            state.controlled_error = ControlledPlannerError(
                code="unknown_execution_reference", message=str(exc)
            )
            return state

        session_id = _session_id(state, runtime) or "default"
        session = get_session(context.database_url)
        try:
            approvals = ExecutionApprovalRepository(session)
            approval = approvals.find_pending(
                session_id=session_id,
                task_id=task_id,
                contract_fingerprint=prepared.contract_fingerprint,
            )
            if approval is None:
                approval = approvals.create(
                    ExecutionApproval(
                        session_id=session_id,
                        task_id=task_id,
                        profile_id=profile_id,
                        hypothesis_id=hypothesis_id,
                        execution_ref=prepared.execution_ref,
                        contract_fingerprint=prepared.contract_fingerprint,
                        prepared_payload=_prepared_payload(prepared),
                    )
                )
        finally:
            session.close()

        state.pending_interaction = PendingUserInteraction(
            kind="execution_approval",
            payload={
                "execution_approval_id": str(approval.execution_approval_id),
                "execution_ref": prepared.execution_ref,
                "contract_fingerprint": prepared.contract_fingerprint,
                "task_id": str(task_id),
                "data_profile_id": str(profile_id),
            },
            allowed_actions=["approve", "cancel", "revise", "clarify"],
            snapshot_hash=prepared.contract_fingerprint,
            proposal_id=str(approval.execution_approval_id),
        )
    return state


@registry.register()
def resume_execution(state: State, runtime: Runtime[Context]) -> State:
    """Reconstruct one pending approval from the durable workflow record."""

    approval_id = state.resume_approval_id
    context = _runtime_context(runtime)
    if approval_id is None or context is None or context.database_url is None:
        state.controlled_error = ControlledPlannerError(
            code="execution_resume_unavailable",
            message="No durable execution approval is available to resume.",
        )
        return state
    session = get_session(context.database_url)
    try:
        approval = ExecutionApprovalRepository(session).get_by_id(approval_id)
    finally:
        session.close()
    if approval is None or approval.session_id != (_session_id(state, runtime) or "default"):
        state.controlled_error = ControlledPlannerError(
            code="invalid_execution_approval",
            message="The requested execution approval does not belong to this session.",
        )
        return state
    if approval.status not in {ExecutionApprovalStatus.PENDING, ExecutionApprovalStatus.APPROVED}:
        state.controlled_error = ControlledPlannerError(
            code="execution_approval_not_pending",
            message="The requested execution approval is no longer resumable.",
        )
        return state

    task_ref = state.bind_object_reference("task", str(approval.task_id))
    profile_ref = state.bind_object_reference("data_profile", str(approval.profile_id))
    hypothesis_ref = (
        state.bind_object_reference("hypothesis", str(approval.hypothesis_id))
        if approval.hypothesis_id is not None
        else None
    )
    prepared_payload = dict(approval.prepared_payload)
    prepared_payload.update(
        {
            "task_ref": task_ref,
            "data_profile_ref": profile_ref,
            "hypothesis_ref": hypothesis_ref,
            "execution_ref": approval.execution_ref,
            "contract_fingerprint": approval.contract_fingerprint,
        }
    )
    state.prepared_execution = PreparedExecution.model_validate(prepared_payload)
    state.execution_preparation = ExecutionPreparation(prepared=True)
    state.task_selection = TaskSelection(task_ref=task_ref, selected=True)
    state.pending_interaction = PendingUserInteraction(
        kind="execution_approval",
        payload={
            "execution_approval_id": str(approval.execution_approval_id),
            "execution_ref": approval.execution_ref,
            "contract_fingerprint": approval.contract_fingerprint,
            "task_id": str(approval.task_id),
            "data_profile_id": str(approval.profile_id),
        },
        allowed_actions=["approve", "cancel", "revise", "clarify"],
        snapshot_hash=approval.contract_fingerprint,
        proposal_id=str(approval.execution_approval_id),
    )
    return state


@registry.register()
def pause(state: State, runtime: Runtime[Context]) -> State:
    """Pause the current process and wait for user input or confirmation."""

    return state


@registry.register()
def process_decision(state: State, runtime: Runtime[Context]) -> State:
    """Validate a user decision; routing is deliberately separate from state updates."""

    interaction = state.pending_interaction
    decision = state.planner_decision
    if interaction is None or decision is None:
        state.interaction_error = "No user approval was supplied for the pending interaction."
        return state
    context = _runtime_context(runtime)
    if context is None or context.database_url is None:
        state.interaction_error = "Execution approval requires a configured planner database."
        return state
    approval_id_text = interaction.payload.get("execution_approval_id")
    try:
        approval_id = UUID(str(approval_id_text))
    except (TypeError, ValueError):
        state.interaction_error = "The pending execution approval is malformed."
        return state
    session = get_session(context.database_url)
    try:
        approvals = ExecutionApprovalRepository(session)
        approval = approvals.get_by_id(approval_id)
        if approval is None or approval.session_id != (_session_id(state, runtime) or "default"):
            state.execution_revalidation = ExecutionRevalidation(
                valid=False,
                error_code="invalid_execution_approval",
                error_message="The approval does not belong to this planner session.",
            )
            return state
        if decision.action != "approve":
            approvals.set_status(approval_id, ExecutionApprovalStatus.CANCELLED)
            return state
        if approval.status == ExecutionApprovalStatus.CONSUMED:
            state.execution_revalidation = ExecutionRevalidation(
                valid=False,
                error_code="execution_already_admitted",
                error_message="This approval has already admitted an execution attempt.",
            )
            return state
        if approval.status != ExecutionApprovalStatus.PENDING:
            state.execution_revalidation = ExecutionRevalidation(
                valid=False,
                error_code="execution_approval_not_pending",
                error_message="This execution approval is no longer pending.",
            )
            return state
        # A legacy in-process caller may omit proposal_id, but cannot supply a
        # different id or fingerprint to authorize another contract.
        if decision.proposal_id is not None and decision.proposal_id != str(approval_id):
            state.execution_revalidation = ExecutionRevalidation(
                valid=False,
                error_code="stale_execution_approval",
                error_message="The approval does not identify the pending execution contract.",
            )
            return state
        approvals.set_status(approval_id, ExecutionApprovalStatus.APPROVED)
    finally:
        session.close()

    if decision.action != "approve":
        return state
    if interaction.kind != "execution_approval" or state.prepared_execution is None:
        state.interaction_error = "The pending interaction is not an execution approval."
        return state
    prepared = state.prepared_execution
    if (
        approval.contract_fingerprint != prepared.contract_fingerprint
        or interaction.snapshot_hash != prepared.contract_fingerprint
        or interaction.payload.get("execution_ref") != prepared.execution_ref
        or (decision.execution_ref is not None and decision.execution_ref != prepared.execution_ref)
    ):
        state.execution_revalidation = ExecutionRevalidation(
            valid=False,
            error_code="stale_execution_approval",
            error_message="The approved execution contract no longer matches the current plan.",
        )
        return state
    state.execution_revalidation = ExecutionRevalidation(valid=True)
    return state


def route_process_decision(state: State, runtime: Runtime[Context]) -> str:
    """Route only after the decision node has recorded its validation result."""

    if state.execution_revalidation is not None and state.execution_revalidation.valid:
        return "approved_execution"
    if state.planner_decision is not None and state.planner_decision.action == "clarify":
        return "clarify"
    return "cancel"


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


def _method_parameter_hash(parameters: list[Any]) -> str:
    """Hash typed method parameters deterministically for contract/result comparison."""

    payload = [
        parameter.model_dump(mode="json") if isinstance(parameter, BaseModel) else parameter
        for parameter in parameters
    ]
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _execution_contract_fingerprint(task: Any, profile: Any, specification: Any) -> str:
    """Bind approval to the exact task, profile, method, variables, and parameters."""

    payload = {
        "task_id": str(task.task_id),
        "task_updated_at": task.updated_at.isoformat(),
        "profile_id": str(profile.profile_id),
        "profile_version_at": getattr(profile, "updated_at", profile.created_at).isoformat(),
        "profile_lifecycle_state": profile.lifecycle_state.value,
        "profile_accepted": profile.accepted_as_ground_truth,
        "variables": specification.variable_bindings,
        "scope": specification.scope,
        "method": specification.validation_method,
        "parameters": [
            parameter.model_dump(mode="json") for parameter in specification.method_parameters
        ],
        "decision_rule": (
            specification.decision_rule.model_dump(mode="json")
            if hasattr(specification.decision_rule, "model_dump")
            else specification.decision_rule
        ),
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _prepared_payload(prepared: PreparedExecution) -> dict[str, Any]:
    """Serialize only durable contract content; local handles are reconstructed on resume."""

    return {
        "task_title": prepared.task_title,
        "dataset_path": prepared.dataset_path,
        "hypothesis": prepared.hypothesis.model_dump(mode="json"),
        "specification": prepared.specification.model_dump(mode="json"),
        "deterministic_seed": prepared.deterministic_seed,
    }


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


def _append_execution_failure(
    state: State,
    runtime: Runtime[Context] | None,
    *,
    run_status: str = "failed",
) -> None:
    """Queue one retryable failure transition for an admitted execution attempt."""

    prepared = state.prepared_execution
    if prepared is None or prepared.execution_run_ref is None or prepared.hypothesis_ref is None:
        return
    try:
        run_id = state.resolve_object_reference(prepared.execution_run_ref)
        hypothesis_id = state.resolve_object_reference(prepared.hypothesis_ref)
    except ValueError:
        return
    if any(
        operation.operation_type == PlannerOperationType.UPDATE_EXECUTION_RUN
        and operation.payload.get("execution_run_id") == run_id
        and operation.payload.get("status") in {"failed", "dispatch_failed"}
        for operation in state.planner_operations
    ):
        return
    session_id = _session_id(state, runtime)
    state.planner_operations.extend(
        [
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.UPDATE_EXECUTION_RUN,
                payload={"execution_run_id": run_id, "status": run_status},
                produced_by_node=PlannerNodeName.REVIEW_EXECUTION,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            ),
            PlannerOperation(
                session_id=session_id,
                operation_type=PlannerOperationType.CHANGE_HYPOTHESIS_STATE,
                payload={
                    "hypothesis_id": hypothesis_id,
                    "status": HypothesisStatus.APPROVED.value,
                },
                produced_by_node=PlannerNodeName.REVIEW_EXECUTION,
                approval_state=PlannerOperationApprovalState.NOT_REQUIRED,
            ),
        ]
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


def _evaluate_deterministically(
    evidence: Evidence,
    rule: EvaluationThresholds,
    *,
    validation_method: str,
) -> HypothesisEvidenceOutcome:
    """Evaluate the only supported method from admitted metrics, never executor advice."""

    if validation_method != "deterministic_test":
        return HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE
    # The narrow method has one understood metric: a finite p-value evaluated
    # against alpha. Other rule shapes require a method-owned evaluator first.
    if rule.p_value is None or rule.effect_size is not None or rule.metric_thresholds:
        return HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE
    metric_name = evidence.result_summary.metric_name
    metric_value = evidence.result_summary.metric_value

    if (
        metric_name != "p_value"
        or not isinstance(metric_value, (int, float))
        or isinstance(metric_value, bool)
    ):
        return HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE
    from math import isfinite

    if not isfinite(metric_value) or not 0.0 <= metric_value <= 1.0:
        return HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE
    if not 0.0 < rule.p_value <= 1.0:
        return HypothesisEvidenceOutcome.INSUFFICIENT_EVIDENCE
    if metric_value < rule.p_value:
        return HypothesisEvidenceOutcome.SUPPORTS
    return HypothesisEvidenceOutcome.INCONCLUSIVE


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
            repository.stage_create(operation)

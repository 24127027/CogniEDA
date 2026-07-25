"""Fail-closed composition root for the supported Wave 1 runtime services."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic_ai.models import Model
from sqlmodel import Session

from agents.executor.dispatcher import DataExplorerDispatcher
from agents.executor.hypothesis_analyst.nodes import build_hypothesis_analyst_agent
from agents.executor.registry import DataExplorerFactory, DataExplorerRegistry
from agents.executor.types import DataExplorerExecutionContext
from agents.planner.agent import Planner
from application.discovery import DiscoveryAdmissionCoordinator
from application.evaluation import (
    enqueue_ready_evaluations,
    run_evaluation_attempt,
)
from application.execution.dispatch import dispatch_pending_attempts
from application.execution.recovery import reconcile_execution_attempts
from application.governance import (
    AuthenticatedPrincipalResolver,
    DiscoveryAdmissionGovernanceService,
    GovernanceAuthorityIssuer,
)
from application.validity import AtomicValidityPropagationService
from db.init_db import init_db
from db.models import GovernanceAuthorityRecord, ProposalDecisionRecord
from db.session import get_session
from schemas.enums import GovernanceDecisionOutcome
from schemas.governance import AuthenticatedPrincipal
from schemas.validity import (
    ValidityPropagationCommand,
    ValidityPropagationResult,
)


class RuntimeConfigurationError(RuntimeError):
    """Raised when a required production adapter was not supplied."""


@dataclass(frozen=True, slots=True)
class RuntimeConfiguration:
    """Non-secret configuration for one workspace-local runtime."""

    database_url: str
    authority_ttl_seconds: int = 900

    def __post_init__(self) -> None:
        if not self.database_url.strip():
            raise RuntimeConfigurationError("Runtime requires an explicit database URL.")
        if self.authority_ttl_seconds < 1:
            raise RuntimeConfigurationError("Authority TTL must be positive.")


class CogniEDARuntime:
    """The only supported owner of Wave 1 service construction."""

    def __init__(
        self,
        configuration: RuntimeConfiguration,
        *,
        principal_resolver: AuthenticatedPrincipalResolver,
        analyst_model: Model,
        data_explorer_id: str,
        data_explorer_factory: DataExplorerFactory,
        executor_context_factory: Callable[[], DataExplorerExecutionContext],
    ) -> None:
        if principal_resolver is None:
            raise RuntimeConfigurationError(
                "Runtime requires a composition-provided authenticated-principal resolver."
            )
        if analyst_model is None:
            raise RuntimeConfigurationError(
                "Runtime requires an explicit Hypothesis Analyst model provider."
            )
        if not data_explorer_id or not data_explorer_id.strip():
            raise RuntimeConfigurationError(
                "Runtime requires an explicit Data Explorer executor identifier."
            )
        if data_explorer_factory is None:
            raise RuntimeConfigurationError(
                "Runtime requires an explicitly registered Data Explorer adapter."
            )
        if executor_context_factory is None:
            raise RuntimeConfigurationError(
                "Runtime requires an explicit Data Explorer context factory."
            )

        self.configuration = configuration
        self._database_url = init_db(configuration.database_url)
        self._principal_resolver = principal_resolver
        self._executor_context_factory = executor_context_factory
        registry = DataExplorerRegistry()
        registry.register_factory(data_explorer_id, data_explorer_factory)
        self._executor_registry = registry
        self._executor_dispatcher = DataExplorerDispatcher(registry)
        self._analyst_agent = build_hypothesis_analyst_agent(model=analyst_model)
        self._planner = Planner(database_url=self._database_url)

    @property
    def planner(self) -> Planner:
        """Return the one Planner graph owned by this composition root."""

        return self._planner

    @property
    def registered_data_explorer_ids(self) -> tuple[str, ...]:
        """Expose the exact Data Explorer adapter identifier for diagnostics."""

        return self._executor_registry.list_executor_ids()

    @contextmanager
    def session(self) -> Iterator[Session]:
        """Open the single configured session-factory semantics for all services."""

        session = get_session(self._database_url)
        try:
            yield session
        finally:
            session.close()

    def resolve_principal(self, authentication_context_id: str) -> AuthenticatedPrincipal:
        """Resolve server-authenticated identity and reject substituted or future context."""

        if not authentication_context_id.strip():
            raise RuntimeConfigurationError("Authentication context identity cannot be empty.")
        principal = self._principal_resolver.resolve_authenticated_principal(
            authentication_context_id
        )
        if principal.authentication_context_id != authentication_context_id:
            raise RuntimeConfigurationError("Authentication resolver substituted context identity.")
        authenticated_at = principal.authenticated_at
        if authenticated_at.tzinfo is None:
            authenticated_at = authenticated_at.replace(tzinfo=UTC)
        if authenticated_at > datetime.now(UTC):
            raise RuntimeConfigurationError("Authenticated principal timestamp is in the future.")
        return principal

    async def dispatch_execution_work(
        self,
        *,
        worker_id: str,
        max_attempts: int = 10,
    ) -> int:
        """Dispatch durable Data Explorer work through the explicit capability registry."""

        with self.session() as session:
            return await dispatch_pending_attempts(
                session,
                self._executor_dispatcher,
                worker_id,
                max_attempts=max_attempts,
                context_factory=self._executor_context_factory,
            )

    def reconcile_execution_work(self) -> None:
        """Recover durable execution stages without in-memory authority."""

        with self.session() as session:
            reconcile_execution_attempts(session)

    def evaluate_ready_hypotheses(
        self,
        *,
        owner: str,
        limit: int = 100,
    ) -> tuple[UUID, ...]:
        """Enqueue and evaluate protected bundles with the explicit Analyst provider."""

        with self.session() as session:
            controls = enqueue_ready_evaluations(session, limit=limit)
            evaluation_ids = tuple(control.evaluation_id for control in controls)
        for evaluation_id in evaluation_ids:
            with self.session() as session:
                run_evaluation_attempt(
                    session,
                    evaluation_id=evaluation_id,
                    owner=owner,
                    agent=self._analyst_agent,
                )
        return evaluation_ids

    def issue_user_authority(
        self,
        authentication_context_id: str,
    ) -> GovernanceAuthorityRecord:
        """Issue fixed-purpose, expiring authority from trusted authentication only."""

        principal = self.resolve_principal(authentication_context_id)
        expires_at = datetime.now(UTC) + timedelta(seconds=self.configuration.authority_ttl_seconds)
        with self.session() as session:
            return GovernanceAuthorityIssuer(
                session,
                principal_resolver=self._principal_resolver,
                workspace_id=principal.workspace_id,
                session_id=principal.session_id,
            ).issue_user_authority(
                authentication_context_id=authentication_context_id,
                expires_at=expires_at,
            )

    def record_proposal_decision(
        self,
        *,
        authentication_context_id: str,
        evaluation_id: UUID,
        authority_id: UUID,
        decision: GovernanceDecisionOutcome,
    ) -> ProposalDecisionRecord:
        """Persist one exact decision under the authenticated workspace/session binding."""

        principal = self.resolve_principal(authentication_context_id)
        with self.session() as session:
            return DiscoveryAdmissionGovernanceService(
                session,
                workspace_id=principal.workspace_id,
                session_id=principal.session_id,
                principal_id=principal.principal_id,
            ).record_governance_decision(
                evaluation_id=evaluation_id,
                authority_id=authority_id,
                decision=decision,
            )

    @contextmanager
    def discovery_admission_coordinator(
        self,
        authentication_context_id: str,
    ) -> Iterator[DiscoveryAdmissionCoordinator]:
        """Open an authenticated coordinator under the one session-factory boundary."""

        principal = self.resolve_principal(authentication_context_id)
        with self.session() as session:
            yield DiscoveryAdmissionCoordinator(
                session,
                workspace_id=principal.workspace_id,
                session_id=principal.session_id,
            )

    def propagate_validity(
        self,
        command: ValidityPropagationCommand,
        *,
        authentication_context_id: str | None = None,
    ) -> ValidityPropagationResult:
        """Execute one atomic validity propagation command under the runtime session."""

        principal = (
            self.resolve_principal(authentication_context_id)
            if authentication_context_id is not None
            else None
        )
        with self.session() as session:
            return AtomicValidityPropagationService(
                session,
                principal_id=principal.principal_id if principal is not None else None,
            ).execute_propagation(command)

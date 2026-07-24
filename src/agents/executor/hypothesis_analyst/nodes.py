"""Isolated PydanticAI evidence-evaluation boundary for Hypothesis Analyst."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models import Model

from schemas.specialist_contracts import (
    DiscoveryProposal,
    DiscoverySynthesisBundle,
    HypothesisAnalystResult,
    validate_proposal_against_bundle,
)

HYPOTHESIS_ANALYST_SYSTEM_PROMPT = """\
You are the CogniEDA Hypothesis Analyst in evidence-evaluation mode.

Use only the protected bundle supplied by typed dependencies. Preserve the exact Hypothesis scope,
DataProfile, method, parameters, decision rule, and complete active Evidence set. Distinguish
observed results from interpretation and return exactly one structured DiscoveryProposal or one
typed EvaluationFailure. Supported, contradicted, inconclusive, and insufficient_evidence are all
scientific proposal outcomes, never technical failures.

For fail-to-reject or non-significant evidence, use inconclusive or insufficient_evidence and state
that the available evidence is insufficient within the supplied scope and method. Never claim that
no relationship or association exists. Carry all Evidence limitations, uncertainty, and required
invalidators into the proposal.

Do not use Assumptions, Tasks, prior Discoveries, SessionFrames, chat history, user decisions,
PlannerOperations, GeneratedViews, cached summaries, raw data, files, repositories, databases, or
tools. Do not create durable IDs or lifecycle operations.
"""


@dataclass(frozen=True, slots=True)
class HypothesisAnalystDependencies:
    """The Analyst's complete dependency surface."""

    bundle: DiscoverySynthesisBundle


class HypothesisAnalystConfigurationError(RuntimeError):
    """Raised when the isolated Analyst provider is not configured."""


def build_hypothesis_analyst_agent(
    *, model: Model | str
) -> Agent[HypothesisAnalystDependencies, HypothesisAnalystResult]:
    """Construct a no-tool, typed-output Analyst with bounded model retries."""

    agent: Agent[HypothesisAnalystDependencies, HypothesisAnalystResult] = Agent(  # type: ignore[call-overload]
        model=model,
        output_type=HypothesisAnalystResult,
        deps_type=HypothesisAnalystDependencies,
        system_prompt=HYPOTHESIS_ANALYST_SYSTEM_PROMPT,
        retries=2,
        tools=(),
        name="cognieda_hypothesis_analyst",
    )

    @agent.instructions
    def _protected_bundle_instruction(
        ctx: RunContext[HypothesisAnalystDependencies],
    ) -> str:
        return (
            "Evaluate this canonical protected bundle. It is the entire scientific input:\n"
            + ctx.deps.bundle.model_dump_json()
        )

    @agent.output_validator
    def _validate_output(
        ctx: RunContext[HypothesisAnalystDependencies],
        output: HypothesisAnalystResult,
    ) -> HypothesisAnalystResult:
        if isinstance(output, DiscoveryProposal):
            try:
                validate_proposal_against_bundle(output, ctx.deps.bundle)
            except ValueError as exc:
                raise ModelRetry(str(exc)) from exc
        return output

    return agent


def evaluate_synthesis_bundle(
    bundle: DiscoverySynthesisBundle,
    *,
    agent: Agent[HypothesisAnalystDependencies, HypothesisAnalystResult],
) -> HypothesisAnalystResult:
    """Invoke the typed PydanticAI boundary without history, tools, or generic context."""

    result = agent.run_sync(
        "Evaluate the supplied protected bundle and return the typed result.",
        deps=HypothesisAnalystDependencies(bundle=bundle),
        message_history=None,
    )
    return result.output

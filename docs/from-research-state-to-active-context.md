# From research state to active context

This workflow follows the running churn investigation from durable research
state to one bounded reasoning context. It applies the concepts owned by
[SessionFrame and active context](session-frame-and-active-context.md),
[Retrieval and context type safety](retrieval-and-context-type-safety.md), and
[Context reconstruction and continuity](context-reconstruction-and-continuity.md).

> **Implementation status:** the Planning Context, bounded Discovery retrieval,
> lifecycle exclusion, profile-aware motivation eligibility, pins, exclusions,
> deterministic lexical ranking, and context projection used here are
> **Implemented**. Complete answer generation is **Partially implemented**.
> Strict operation-scope filtering and parent-task GeneratedViews are
> **Design target** areas, and automatic resume is **Unsupported**.

## Starting state

The retention team is investigating:

> Within the 2025 small-business subscription cohort, is longer first-response
> time associated with 90-day churn?

Durable state now contains:

- an active Objective to understand actionable churn drivers;
- an accepted DataProfile for the current 2025 cohort;
- an organizing parent Task and analytical child Tasks;
- a planning Assumption about the account-month grain;
- one active Discovery about first-response time and churn;
- an older Discovery derived from a previous DataProfile;
- the evaluated Hypotheses and Evidence behind those Discoveries; and
- a SessionFrame with selected state, a user pin, and an exclusion.

Storage alone does not decide what the next operation may use.

## The conceptual workflow

For each operation, CogniEDA should follow:

```text
current operation
  -> determine context mode
  -> retrieve candidate typed state
  -> filter by authority, lifecycle, DataProfile, scope, and epistemic type
  -> rank the remaining candidates deterministically
  -> apply admissible user governance
  -> construct a bounded active context
  -> perform planning or answer work
```

In current Discovery retrieval, user governance is not one final step.
Exclusions are applied before scoring, while pins add candidate-pool membership
and structural priority during ranking. Lifecycle invalidity still wins over
both. A profile mismatch becomes a warned context-only result rather than being
fully removed, and an independent operation-scope filter is not yet present.

That difference is a **Known deviation** from the stronger conceptual pipeline.

## 1. The operation chooses the context type

Suppose the user asks to decompose the churn-driver parent Task. This is a
planning operation, so Planning Context may include active Tasks and planning
Assumptions. It may also use current Discoveries as motivation.

If the user instead asks a question, Answer Context should exclude Assumptions
and workflow Tasks while allowing current Discoveries and active Evidence.
Current answer policy exists, but the Planner answer path is
**Partially implemented**.

If the operation is protected scientific evaluation, SessionFrame context is
not used at all. The application rebuilds Protected Conclusion Context from
authoritative repositories as described in
[Protected evaluation context](protected-evaluation-context.md).

## 2. The selected SessionFrame is checked

The caller supplies the frame identifier. The Planner reloads it from the same
workspace-local database. A superseded or archived frame cannot produce
Planning Context.

For an eligible frame, the projection may contribute the Objective wording,
current DataProfile reference, active Tasks, the active grain Assumption,
warnings, and selected research summaries. Cached tool summaries are not
projected into the Planner context.

The frame helps reconstruct selection. It does not prove that every selected
object is still authoritative, so repository-backed retrieval re-reads
Discovery state.

## 3. The active Discovery is admitted for planning

The current Discovery says that longer first-response time is associated with
90-day churn within the accepted 2025 small-business cohort. Its lifecycle is
active and its validity basis names the active DataProfile.

It may enter the bounded candidate pool through parent-Task motivation, a frame
reference, a valid pin, or the recent Discovery window. A profile match and
structural relationship contribute to ranking. If selected as a motivation,
the later Task commit revalidates its lifecycle and DataProfile again.

This is **Implemented**. Retrieval creates no durable scientific state; it only
provides typed proposal context and inclusion reasons.

## 4. The old DataProfile Discovery stays context-only

An older churn Discovery may contain very similar words but refer to a prior
cohort snapshot. Current retrieval flags the mismatch and marks the Discovery
ineligible to motivate the new Task. Planner prompts distinguish selectable
motivation from context-only references, and commit rejects a selected
motivation that does not match the bounded DataProfile.

The old Discovery may still appear in the ranked context-only set and consume
part of the context budget. It is not silently promoted, because its warning and
motivation ineligibility are explicit. Removing it before ranking or allowing
an explicit comparative cross-profile operation is a **Design target**.

## 5. The Assumption is allowed only for planning

The Assumption says each row represents one account-month. That may help the
Planner decide whether a grain-validation Task is needed. It is therefore
admissible in Planning Context.

It is excluded from Answer Context by default and structurally absent from the
protected scientific bundle. If the Assumption matters to the churn claim, the
system must turn it into something testable and obtain Evidence; confidence or
a user pin cannot make it an inference premise.

## 6. The completed Hypothesis remains historical

The Hypothesis that produced the current Discovery has already been evaluated.
It remains durable for lineage, but it is excluded from ordinary future context
by default.

Future planning should retrieve the active Discovery as the evidence-bound
claim. The evaluated Hypothesis remains the historical test contract that
explains how that Discovery was produced; it does not compete with its own
result as current knowledge.

## 7. An invalidated pinned Discovery stays historical

Suppose the user pinned another churn Discovery, then its supporting Evidence
was invalidated.

The pin remains understandable as historical user intent. When retrieval
encounters it, the engine reloads the Discovery, sees invalidated lifecycle
state, excludes it before scoring, and records an exclusion note. The pin does
not restore authority.

If the affected frame includes the Discovery or its lineage through the
dependency fields used by validity propagation, the frame becomes superseded.
A frame with only a pin may remain active-status, and no automatic successor or
user-facing notice is generated. Active retrieval is safe; frame-refresh
experience is **Partially implemented**.

## 8. Exclusions remove otherwise admissible context

If the user excludes a current but irrelevant Discovery, the engine removes it
before scoring. An exclusion also wins over a pin.

This is ordinary context governance. It does not invalidate or delete the
Discovery. Another explicit operation may still read it historically, and a
future successor frame may change the selection.

## 9. Ranking stays downstream of authority

The remaining candidates receive structural and lexical scores. Direct
motivation outranks ancestor motivation; pins have strong priority; matching
DataProfile state helps; and deterministic token overlap measures local
relevance.

Results sort by score, creation time, and stable identifier before one visible
budget is applied. No embedding, vector store, persistent semantic index, or
Graph Miner participates.

Lexical ranking is inspectable and reproducible, but it misses paraphrases,
synonyms, conceptual relationships, and multi-hop graph structure. Future
ranking may improve those weaknesses only after authority and admissibility
gates.

## 10. The bounded context supports a proposal, not a conclusion

The Planner receives:

- Objective constraints;
- the planning-only Assumption;
- selectable current-profile Discovery motivation;
- context-only warned Discoveries;
- inclusion explanations; and
- retrieval exclusion notes.

It may propose child Tasks with explicit motivation and analytical contracts.
Those proposals still require approval and commit. Neither the context nor the
model response becomes Evidence or Discovery.

This distinction prevents relevance from laundering planning material into
scientific knowledge.

## 11. A parent Task needs a GeneratedView

Later, the user may ask, “What did we learn about churn drivers?” The parent
Task itself has no Hypothesis and cannot produce a Discovery.

The target answer path should:

```text
find terminal analytical child Tasks
  -> retrieve their active Discoveries
  -> consult supporting Evidence when presentation requires it
  -> build a bounded GeneratedView
```

The view may summarize first-response time, pricing, and support-quality
findings without pretending one Evidence set proved a combined parent claim.
After a validity change it can be regenerated from current descendants.

Task hierarchy and individual Discovery lineage are **Implemented**.
The complete parent-task query, GeneratedView contract, synthesis service, and
answer product are a **Design target**.

## What the workflow protects

| Situation | Active-context result | Invariant protected |
| --- | --- | --- |
| active Discovery on current DataProfile | selectable for planning motivation | current authority and profile binding |
| similar Discovery on another DataProfile | warned context-only result | no silent cross-profile motivation |
| active Assumption | planning only | provisional belief cannot support a conclusion |
| evaluated Hypothesis | historical lineage, excluded by default | test contract does not replace durable knowledge |
| invalidated pinned Discovery | excluded with a note | a pin cannot override validity |
| explicit exclusion | removed from ordinary retrieval | user selection does not mutate truth |
| parent Task answer | future GeneratedView over child Discoveries | narrative synthesis does not become untested knowledge |
| protected evaluation | separate repository-built bundle | SessionFrame and retrieval context cannot become scientific premises |

## Current boundary

- **Implemented:** Planning Context projection, bounded Discovery retrieval,
  lifecycle exclusion, pins and exclusions, profile-aware motivation
  eligibility, deterministic lexical scoring, and commit revalidation.
- **Verified on SQLite:** the focused lifecycle, transaction, and active
  exclusion paths covered by current tests.
- **Partially implemented:** Answer Context product use, SessionFrame
  governance, automatic context refresh, strict profile admission, and
  session-resume experience.
- **Known deviation:** wrong-profile Discoveries may rank as context-only;
  Objective and SessionFrame request identifiers do not filter repository
  candidates; independent operation-scope filtering is absent.
- **Design target:** parent-task GeneratedViews and explicit cross-profile
  comparison.
- **Deferred:** semantic or vector retrieval, persistent indexing, Graph Miner,
  and the complete validity-over-time narrative.
- **Unsupported:** automatic workspace reopening, restored chat, distributed
  retrieval, and multi-user context governance.

## Implementation orientation

The implemented workflow crosses `src/agents/planner/`, `src/memory/`,
`src/schemas/retrieval.py`, and the research and Discovery repositories.
Protected evaluation remains under `src/application/evaluation/`.

Focused verification is under `tests/memory/`, `tests/architecture/`,
`tests/agents/planner/`, `tests/application/`, and `tests/e2e/`.

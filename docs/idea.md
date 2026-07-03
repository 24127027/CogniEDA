You are working on a project called CogniEDA.

CogniEDA is not just an exploratory data analysis tool. It is an agentic data investigation system designed for long-running, evidence-based analytical work.

The project focuses on two core problems:

1. Deep data investigation:
   The agent should not merely generate charts or quick summaries. It should investigate datasets through a disciplined loop of profiling, questioning, assumption tracking, hypothesis generation, hypothesis validation, evidence creation, and iterative refinement.

2. Memory and context management:
   The agent should be able to work across long sessions without suffering from context rot. It must know what to remember, what to forget, what to mark as stale, what to keep active, what to archive, and what must be revalidated.

CogniEDA should be understood as a system for turning messy data exploration into structured, traceable knowledge.

Its goal is not to make agents “remember more.” Its goal is to make agents remember the right things, forget in a controlled way, reason from valid context, and avoid using stale or unsupported information.

## Core Philosophy

CogniEDA treats every dataset as an object of investigation, not as a source of truth.

When a dataset is imported, uploaded, or created, the agent must not assume that the dataset is reliable, complete, representative, correctly typed, semantically valid, or suitable for the user’s analytical question.

A dataset can be technically readable but analytically dangerous.

It may contain:

- missing values,
- duplicate rows,
- invalid values,
- wrong data types,
- inconsistent timestamps,
- incorrect timezone assumptions,
- hidden preprocessing,
- inconsistent units,
- sampling bias,
- tracking errors,
- schema drift,
- incorrect joins,
- outliers,
- measurement bias,
- incomplete target variables,
- unclear business definitions,
- or values whose meaning is unknown.

Therefore, the agent must not say “this dataset is trustworthy” simply because it exists.

Trust must be earned through evidence.

CogniEDA should force the agent to reason like this:

- “This dataset has not been validated yet.”
- “This column appears usable for this specific purpose, but only under these assumptions.”
- “This conclusion depends on a dataset version that may now be stale.”
- “This hypothesis is supported by current evidence, but the evidence is weak because the target variable has high missingness.”
- “This dataset is good enough for traffic trend analysis, but not good enough for causal claims about churn.”

The system should help the agent avoid premature conclusions.

A good CogniEDA agent should be comfortable saying:

- “I do not have enough evidence.”
- “This is only an observation, not a conclusion.”
- “This hypothesis is currently inconclusive.”
- “This result depends on an unvalidated assumption.”
- “The dataset is not fit for this question.”
- “This conclusion should be revalidated because the dataset version changed.”

CogniEDA should reward honest analysis over confident speculation.

## Dataset as Asset, Not Truth

A dataset should first be understood as a data asset.

A data asset is a specific version of data that can be referenced, profiled, transformed, validated, and traced.

The dataset asset answers questions like:

- What dataset is this?
- Where did it come from?
- Which project does it belong to?
- Is it raw, cleaned, transformed, sampled, joined, aggregated, or derived?
- Which version is it?
- What previous dataset version was it derived from?
- Which operation created it?
- Can we roll back to an earlier version?
- Which evidence, assumptions, hypotheses, or conclusions depend on it?

The dataset asset itself is not evidence.

The dataset is the object being observed.

Evidence is created by observing, profiling, validating, testing, or analyzing the dataset.

For example:

Dataset asset:

- `orders_raw_v1.csv`
- `orders_cleaned_v2.parquet`
- `events_joined_v3`
- `customers_sampled_v4`

Evidence:

- “`orders_raw_v1` contains 351 duplicate `order_id` values.”
- “`events_joined_v3` has 12% missing values in `user_id`.”
- “`customers_sampled_v4` contains only users from paid campaigns.”
- “After removing duplicates, row count changed from 100,000 to 99,649.”
- “The correlation between marketing spend and revenue is 0.74 on dataset version v2.”
- “The validation result for hypothesis H7 is inconclusive because sample size is too small.”

CogniEDA must clearly distinguish:

- dataset asset,
- dataset profile,
- evidence,
- assumption,
- hypothesis,
- validation result,
- insight,
- conclusion,
- memory.

A dataset asset is not evidence.

A profile is not the dataset itself.

An assumption is not a conclusion.

A hypothesis is not validated until evidence supports or contradicts it.

A conclusion should not exist without provenance.

## Dataset Versioning Is Essential

Dataset version control is not optional in CogniEDA.

EDA agents often transform data:

- raw dataset,
- cleaned dataset,
- normalized dataset,
- deduplicated dataset,
- joined dataset,
- filtered dataset,
- sampled dataset,
- feature-engineered dataset,
- aggregated dataset,
- model input dataset.

Each transformation can change the meaning of later results.

If the agent validates a hypothesis on `dataset_v2`, and later discovers that `dataset_v2` was created by an incorrect preprocessing step, then every evidence item, validation result, insight, or conclusion based on `dataset_v2` may need to be marked stale or revalidated.

Without dataset versioning, the system cannot answer:

- Which dataset version produced this conclusion?
- Which preprocessing step created this evidence?
- Which hypothesis depends on this dataset?
- Which validation results are now stale?
- Can we roll back to the version before the faulty transformation?
- Did the issue exist in the raw data or was it introduced by preprocessing?

Dataset versioning is not just storage management.

It is reasoning protection.

It protects the analytical chain from silent corruption.

## Data Quality Is Not a Static Property

CogniEDA should not treat data quality as a single global score.

A dataset may be suitable for one question and unsuitable for another.

For example:

- An event log may be good enough for traffic trend analysis but not for conversion analysis if purchase events are missing.
- A customer survey may be useful for satisfaction analysis but not representative of the full user base.
- A transaction dataset may be valid for revenue totals but invalid for user-level behavior if one row is an item, not an order.
- A cleaned dataset may satisfy technical rules but still suffer from sampling bias or semantic ambiguity.

Therefore, CogniEDA should evaluate “fitness for purpose.”

The agent should ask:

- What question is the user trying to answer?
- Which columns are needed?
- Are those columns complete?
- Are their meanings clear?
- Are the metrics well-defined?
- Is the population represented correctly?
- Is the time window appropriate?
- Are there known biases?
- Are the assumptions acceptable?
- Is the dataset version current?

Data quality should be understood in layers:

1. Technical quality:
   Types, formats, missing values, duplicates, valid ranges.

2. Semantic correctness:
   Whether the values mean what the agent thinks they mean.

3. Business validity:
   Whether the metric definitions match the real business concepts.

4. Fitness for purpose:
   Whether this dataset can answer this specific analytical question.

A “clean” dataset is not necessarily a “true” dataset.

Clean data means it satisfies certain technical rules.

It does not automatically mean it is representative, unbiased, semantically correct, or suitable for causal conclusions.

## Evidence-First Reasoning

CogniEDA should be evidence-first.

No important conclusion should stand without evidence.

Evidence is a structured observation produced by a method, on a specific dataset version, under specific assumptions.

Evidence should answer:

- What was observed?
- On which dataset version?
- Using what method?
- With what metric?
- With what result?
- Under which assumptions?
- With what confidence?
- With what limitations?
- Does it support or contradict a hypothesis?
- Does it depend on stale data?
- Can it be reproduced?

Weak evidence example:

- “Revenue seems higher in June.”

Stronger evidence example:

- “On `orders_cleaned_v2`, total revenue in June is 1.2M compared with 900K in May, a 33% increase. However, the dataset has not yet been checked for June completeness, so this should remain an observation, not a final conclusion.”

Evidence can come from:

- dataset profiling,
- data quality checks,
- schema validation,
- statistical tests,
- correlation analysis,
- distribution comparison,
- anomaly detection,
- model evaluation,
- sensitivity analysis,
- manual user confirmation,
- external documentation,
- code inspection,
- lineage information,
- repeated validation across dataset versions.

Evidence should have strength.

Not all evidence is equal.

Weak evidence may come from:

- small samples,
- unclear metric definitions,
- many unvalidated assumptions,
- high missingness,
- stale dataset versions,
- correlation-only analysis,
- non-representative samples,
- unreproducible tool results.

Strong evidence tends to have:

- clear dataset version,
- clear method,
- reproducible computation,
- appropriate metric,
- sufficient sample size,
- validated assumptions,
- stable results across slices or time windows,
- known limitations,
- explicit provenance.

CogniEDA should not treat all evidence as equally trustworthy.

## Observation, Evidence, Insight, and Conclusion

CogniEDA should distinguish different levels of analytical maturity.

Observation:

A raw pattern noticed in the data.

Example:

- “Revenue appears higher in June than in May.”

Evidence:

An observation with method, metric, dataset version, and scope.

Example:

- “On `orders_cleaned_v2`, June revenue is 33% higher than May revenue.”

Insight:

A meaningful interpretation built from one or more evidence items.

Example:

- “The revenue increase appears to be driven more by order volume than by average order value.”

Conclusion:

A stronger claim with confidence, caveats, and provenance.

Example:

- “Within the current dataset, June revenue growth is mainly explained by higher order volume. However, this does not establish that marketing caused the increase because campaign timing, seasonality, and tracking completeness have not yet been validated.”

The agent must not jump directly from observation to conclusion.

CogniEDA should encourage this progression:

Observation → Evidence → Hypothesis → Validation → Insight → Conclusion.

## Assumptions

An assumption is a temporary working belief used to proceed with analysis when certainty is not yet available.

Assumptions are dangerous because they silently shape downstream reasoning.

Examples:

- “Each row represents one user.”
- “Each row represents one session.”
- “`customer_id` uniquely identifies a customer.”
- “`created_at` is in UTC.”
- “`price` is in USD.”
- “Missing `income` means the user refused to answer.”
- “Duplicate rows are ingestion errors.”
- “Outliers are invalid data.”
- “The dataset represents the full user population.”
- “The target variable is correctly tracked.”
- “The training period and evaluation period use the same schema.”

Assumptions should never be buried in conversation history.

They should be treated as managed analytical objects with status.

Possible assumption statuses:

- proposed,
- active,
- tentative,
- validated,
- rejected,
- risky,
- stale,
- superseded,
- needs review.

An assumption should be traceable to its source:

- inferred by the agent,
- confirmed by the user,
- supported by a data check,
- supported by documentation,
- contradicted by evidence,
- inherited from a previous frame,
- carried over from a previous dataset version.

If an assumption is wrong, not every hypothesis automatically becomes wrong, but any hypothesis depending on that assumption becomes suspicious.

For example:

Assumption:

- “Each row is a user.”

Hypothesis:

- “Users with more sessions have higher conversion.”

If the assumption is false and each row is actually a session, user-level aggregation may be invalid.

CogniEDA should perform dependency-aware reasoning:

- Which hypotheses depend on this assumption?
- Which evidence was generated under this assumption?
- Which conclusions should be downgraded?
- Which validation results should be marked stale?
- Which analyses must be rerun?
- Which memory items should be superseded?

Assumptions can also become hypotheses when they need to be tested.

Example:

Initial assumption:

- “`user_id` uniquely identifies a user.”

Testable hypothesis:

- “No `user_id` maps to multiple emails or multiple real-world identities in the current dataset version.”

CogniEDA should allow assumptions to evolve into validation tasks.

## Hypotheses

A hypothesis is a testable analytical claim.

It should be specific enough to validate, refute, or mark inconclusive.

Good hypotheses:

- “Users with more sessions in the first 7 days have higher retention.”
- “Paid campaign users have lower day-30 retention than organic users.”
- “Orders with higher discount rates have lower profit margins.”
- “Support response time is associated with churn probability.”
- “Missing income is associated with age group and should not be treated as random.”
- “Users who complete onboarding have higher activation rates.”

Weak hypotheses:

- “User behavior is interesting.”
- “Marketing affects revenue.”
- “There is some pattern.”
- “Customers are unhappy.”
- “The data looks strange.”

Weak hypotheses may be useful as seeds, but the agent should refine them before validation.

A hypothesis should have a lifecycle.

Possible hypothesis statuses:

- proposed,
- refined,
- ready to validate,
- validating,
- supported,
- contradicted,
- inconclusive,
- rejected,
- stale,
- needs more data,
- blocked.

A good hypothesis should be linked to:

- the dataset version,
- the relevant assumptions,
- the metric definition,
- the validation method,
- the evidence produced,
- the result,
- the confidence level,
- the limitations,
- and any follow-up hypotheses.

A hypothesis can generate new hypotheses.

For example:

Initial hypothesis:

- “Paid users have lower retention than organic users.”

Validation result:

- Supported overall, but only for mobile users.

New hypothesis:

- “The retention gap between paid and organic users is stronger on mobile than desktop.”

CogniEDA should treat analysis as an iterative hypothesis engine.

## If an Assumption Is Wrong

If an assumption is rejected, CogniEDA should not blindly delete all related work.

Instead, it should analyze impact.

Some hypotheses may be invalid.

Some evidence may still be useful but require reinterpretation.

Some conclusions may be downgraded rather than fully rejected.

For example:

Assumption:

- “Each row is a transaction.”

Hypothesis:

- “Average revenue per transaction increases on weekends.”

If each row is actually an item within an order, then the hypothesis may be invalid as stated.

But an observation like:

- “The number of rows increases on weekends.”

may still be true, although its business meaning changes.

CogniEDA should support graceful degradation:

- validated → supported with caveat,
- supported → inconclusive,
- conclusion → observation,
- active memory → stale memory,
- assumption → rejected,
- hypothesis → needs revalidation.

This makes the system resilient to changing understanding.

## Preprocessing Creates Assumptions

Preprocessing is not a neutral technical activity.

Every preprocessing decision carries assumptions.

Examples:

Median imputation assumes the median is an acceptable replacement.

Dropping missing values assumes missingness does not bias the result.

Removing outliers assumes they are errors rather than meaningful extreme cases.

Deduplicating by email assumes email identifies a person.

Deduplicating by order ID assumes repeated order IDs are invalid duplicates.

Parsing dates assumes a date format.

Converting currency assumes an exchange rate and time of conversion.

Filtering rows assumes those rows are irrelevant or invalid.

Joining datasets assumes the join key is valid.

Sampling assumes the sample remains representative.

Therefore, every important preprocessing step should produce:

- a new dataset version,
- an explanation of what changed,
- evidence describing the change,
- assumptions introduced,
- possible risks,
- and affected downstream hypotheses.

The agent should never silently transform data and continue as if nothing happened.

## Missing Data Is a Signal

Missing data should not automatically be treated as an error.

Missingness can mean many things:

- value not applicable,
- user refused to answer,
- tracking failure,
- data not yet synced,
- event did not occur,
- field hidden by privacy rules,
- business process skipped,
- optional field,
- survey non-response,
- downstream join failure.

Examples:

If `cancel_reason` is missing for non-cancelled orders, that may be expected.

If `cancel_reason` is missing for 80% of cancelled orders, that is a serious data quality issue.

If `income` is missing mostly among younger users, missingness may be informative and not missing completely at random.

The agent should investigate missingness before deciding how to handle it.

It should ask:

- Where is missingness concentrated?
- Is it random?
- Does it depend on another column?
- Does it affect the target variable?
- Does it block a hypothesis?
- Does it require a new assumption?
- Is it a data quality issue or a meaningful category?

CogniEDA should treat missing data as both a quality concern and a potential analytical signal.

## Outliers Should Not Be Removed Too Quickly

Outliers may be errors, but they may also be insights.

Examples:

- A huge transaction may be fraud.
- A highly active user may be a power user.
- A traffic spike may be caused by a campaign.
- A revenue spike may be caused by duplicate ingestion.
- A long session duration may indicate a tracking bug.
- A rare value may reveal an important edge case.

The agent should classify outliers before acting:

- likely data error,
- valid extreme case,
- business event,
- tracking issue,
- unknown.

If the agent removes outliers, it must record:

- why they were removed,
- which rule was used,
- how many rows were affected,
- which dataset version was created,
- which evidence supports the action,
- which assumptions were introduced,
- which hypotheses may be affected.

Outlier handling should be traceable.

## Correlation Is Not Causation

CogniEDA must be careful with causal language.

If the agent finds that A is associated with B, it must not automatically conclude that A causes B.

Example:

Observation:

- “Users who receive more emails have higher conversion.”

Possible explanations:

- Emails increase conversion.
- More active users receive more emails.
- Campaign targeting selects users already likely to convert.
- Users with stronger purchase intent trigger more email events.
- Tracking is biased toward engaged users.

The agent should distinguish:

- association,
- prediction,
- explanation,
- causation.

Causal claims require stronger evidence than correlations.

The agent should say:

- “This is an association, not proof of causality.”
- “This result may be confounded.”
- “A causal conclusion would require experiment design, quasi-experimental analysis, or stronger assumptions.”

CogniEDA should prevent agents from turning correlation into unjustified business conclusions.

## Confidence Is Not a Feeling

Confidence should not be a vague model feeling.

Confidence should be derived from analytical conditions.

Factors affecting confidence include:

- data quality,
- sample size,
- missingness,
- metric clarity,
- assumption validity,
- evidence strength,
- method appropriateness,
- reproducibility,
- consistency across slices,
- sensitivity to preprocessing,
- dataset version freshness,
- risk of bias,
- and degree of causal ambition.

A statistically significant result may still have low confidence if:

- the target variable is unreliable,
- the metric is poorly defined,
- the sample is biased,
- the dataset version is stale,
- the effect is driven by outliers,
- or key assumptions are unvalidated.

A conclusion should expose its confidence and caveats.

## Conclusions Must Have Provenance

A conclusion should never stand alone.

For any conclusion, the agent should be able to answer:

- Which dataset version supports it?
- Which evidence supports it?
- Which assumptions does it depend on?
- Which metric definition was used?
- Which validation method was used?
- What is the confidence level?
- What are the limitations?
- What would make it stale?
- What should be revalidated if data changes?
- What open questions remain?

Bad conclusion:

- “Organic users retain better.”

Better conclusion:

- “On `events_cleaned_v3`, organic users show higher day-30 retention than paid users. This is supported by cohort analysis using the current retention definition. Confidence is medium because paid users have a shorter observation window and campaign-level targeting has not been controlled.”

CogniEDA should push every conclusion toward this standard.

## Rejected Ideas Are Valuable

Rejected ideas should not disappear.

They help prevent repeated mistakes.

Examples:

- “Do not use row count as user count because each row is a session.”
- “Do not median-impute income because missingness depends on age group.”
- “Do not validate churn hypotheses on dataset v1 because the target variable is missing in 35% of records.”
- “Do not use correlation alone to claim marketing caused revenue growth.”
- “Do not use `customer_id` as unique identity because it maps to multiple emails.”

Rejected ideas should be remembered as warnings, not as active truths.

The agent should not reason from rejected ideas as if they were correct, but it should use them to avoid repeating dead ends.

## The Agent Should Know When Not to Conclude

A strong analytical agent is not one that always produces insights.

A strong analytical agent knows when a conclusion is not justified.

CogniEDA should encourage:

- uncertainty,
- caveats,
- blocked conclusions,
- inconclusive validation,
- requests for missing definitions,
- warnings about data suitability,
- and explicit limits of the dataset.

Examples:

- “The dataset can support behavioral analysis, but not causal explanation.”
- “This hypothesis cannot be validated because the required target variable is missing.”
- “The pattern is visible, but it may be driven by seasonality.”
- “The result depends heavily on how retention is defined.”
- “This conclusion should remain tentative until the timezone issue is resolved.”

This is a feature, not a weakness.

## Deep Data Investigation Loop

CogniEDA should guide the agent through a disciplined loop:

1. Understand the user’s analytical goal.
2. Identify the current dataset and dataset version.
3. Profile the dataset.
4. Detect data quality issues.
5. Generate initial observations.
6. Identify required assumptions.
7. Mark risky assumptions.
8. Generate testable hypotheses.
9. Prioritize hypotheses based on relevance, value, and feasibility.
10. Validate hypotheses using appropriate methods.
11. Produce evidence.
12. Update hypothesis status.
13. Update assumption status.
14. Detect new data issues.
15. Create or update dataset versions if preprocessing is needed.
16. Mark affected evidence or conclusions as stale when dependencies change.
17. Store important memory.
18. Archive or mark dead ends.
19. Generate next questions.
20. Repeat.

The loop is not linear.

Validation may reveal new data quality issues.

Data quality issues may invalidate assumptions.

Invalid assumptions may make hypotheses stale.

New evidence may produce new hypotheses.

New dataset versions may require revalidation.

CogniEDA should support this recursive, investigative process.

## Hypothesis Generation Should Be Purposeful

The agent should not generate random hypotheses just because columns exist.

Hypotheses should be prioritized by:

- relevance to the user’s goal,
- potential analytical value,
- feasibility with available data,
- quality of required columns,
- number of unvalidated assumptions,
- potential impact,
- novelty,
- and ability to guide next actions.

Hypotheses can come from:

- user goals,
- dataset schema,
- data profile,
- missingness patterns,
- outliers,
- correlations,
- time trends,
- segment differences,
- domain knowledge,
- failed assumptions,
- previous validation results,
- user feedback,
- external documentation,
- metric definitions.

The agent should transform vague ideas into testable hypotheses.

Example seed idea:

- “Marketing may affect revenue.”

Refined hypotheses:

- “Revenue increased after campaign start date compared with the previous baseline period.”
- “The increase is stronger among users exposed to the campaign.”
- “The revenue increase is driven by order volume rather than average order value.”
- “The observed increase remains after excluding known seasonal periods.”

CogniEDA should help move from vague curiosity to structured validation.

## User Feedback as Evidence

User feedback can be a critical source of evidence.

Examples:

- “Each row is a session, not a user.”
- “Timezone is Asia/Ho_Chi_Minh.”
- “Revenue means estimated revenue, not actual revenue.”
- “Missing value in this field means not applicable.”
- “The campaign started on June 12.”
- “This dataset only includes paid users.”
- “This column was deprecated after March.”

User feedback should not be lost in chat history.

It should be stored with provenance:

- who provided it,
- when it was provided,
- what it applies to,
- which dataset version it applies to,
- which assumptions it validates or rejects,
- which hypotheses it affects.

User feedback can validate, reject, or supersede assumptions.

## Memory Is Context Control, Not Just Long-Term Storage

CogniEDA’s memory system should not be a simple long-term memory database.

It should be a context control layer.

The memory system decides:

- what the agent should actively know,
- what should be excluded from active context,
- what should be pinned,
- what should be pruned,
- what should be archived,
- what should be marked stale,
- what should be treated as warning,
- what should be revalidated,
- what should be passed to another agent,
- what should be cached instead of recomputed.

The goal is not to store everything.

The goal is to control what information is allowed to influence reasoning.

Memory must protect the agent from context rot.

Context rot happens when the agent:

- forgets the original goal,
- uses rejected assumptions,
- confuses dataset versions,
- repeats dead-end analyses,
- treats stale evidence as current,
- repeats expensive tool calls,
- loses important decisions during summarization,
- mixes branches,
- trusts old conclusions,
- or cannot distinguish exploratory thoughts from validated knowledge.

CogniEDA should treat context as a managed resource.

The context window is limited.

The active context should contain only the smallest set of relevant, fresh, high-value information needed for the current task.

## Conversation Context Is Not a Passive Scroll Buffer

CogniEDA should not treat the conversation as a passive transcript.

A long conversation contains many kinds of information:

- confirmed facts,
- guesses,
- failed attempts,
- questions,
- tool outputs,
- outdated results,
- corrections,
- decisions,
- changes of direction,
- user preferences,
- partial plans,
- rejected ideas,
- unresolved issues,
- and temporary reasoning.

The agent must not treat all of these equally.

A conversation should be transformed into structured context.

CogniEDA should introduce the idea of a Context Frame.

A Context Frame is a bounded unit of work.

It has:

- a topic,
- a goal,
- a start boundary,
- an end boundary,
- status,
- decisions,
- assumptions,
- hypotheses,
- evidence,
- tool results,
- open questions,
- dead ends,
- outcome,
- and handoff summary.

A frame is not merely a summary.

It is a structured work product.

Examples of context frames:

- “Profile customer dataset v1.”
- “Investigate missing values in income.”
- “Validate retention hypothesis H3.”
- “Explore churn definition.”
- “Test preprocessing branch without outlier removal.”
- “Review dataset lineage after join failure.”
- “Summarize evidence for marketing revenue hypothesis.”

Each frame should produce a compressed, reusable form of knowledge.

Raw conversation should become:

Conversation → Context Frame → Pruned Frame → Memory Graph → Active Context for future work.

This makes the agent session-aware.

## Memory Should Have Scope

Not all memory belongs everywhere.

CogniEDA should distinguish memory scopes.

Turn memory:

Information from a specific turn.

Frame memory:

Information relevant to a bounded task or topic.

Workspace-level memory:

Long-lived goals, constraints, and decisions for the whole project.

Dataset memory:

Version-specific facts, profiles, quality issues, lineage, and transformations.

Assumption memory:

Assumptions, status, evidence, dependencies, and invalidation rules.

Hypothesis memory:

Hypotheses, validation status, evidence, confidence, and caveats.

Evidence memory:

Evidence items with method, dataset version, result, confidence, and limitations.

Tool cache memory:

Reusable results from expensive tool calls.

Handoff memory:

Compressed context passed from one agent to another.

The agent should retrieve memory based on the current task, not load everything.

For example, when validating a retention hypothesis, active context should include:

- retention metric definition,
- active dataset version,
- relevant assumptions,
- prior retention evidence,
- known data quality issues,
- open questions about retention,
- validation history for related hypotheses.

It should not include unrelated revenue hypotheses, old dead-end branches, or stale dataset profiles unless needed.

## Memory Should Have Status

Every memory item should have a status.

Possible statuses:

- active,
- pinned,
- tentative,
- validated,
- rejected,
- stale,
- superseded,
- archived,
- dead_end,
- overruled,
- unresolved,
- needs_review,
- blocked.

Examples:

Bad memory:

- “`customer_id` is unique.”

Better memory:

- “Assumption A1: `customer_id` uniquely identifies a customer. Status: rejected. Reason: 2.3% of customer IDs map to multiple emails in dataset v1. Impact: user-level aggregation based on customer_id requires review.”

Bad memory:

- “Income missingness is a problem.”

Better memory:

- “Evidence E12: `income` is missing in 28% of rows in `customers_v1`. Missingness is concentrated in age group 18–24. Status: active for dataset v1. Impact: median imputation should not be used without further analysis.”

Status prevents stale or rejected information from contaminating active reasoning.

## Memory Should Have Provenance

Every memory item should know where it came from.

Possible sources:

- user confirmation,
- agent inference,
- dataset profiling,
- data quality check,
- statistical validation,
- tool result,
- external documentation,
- code inspection,
- previous context frame,
- validation result,
- manual annotation.

Provenance matters because sources have different reliability.

A user-confirmed business definition is different from an agent guess.

A tool result from dataset v1 is different from a tool result from dataset v3.

An external document may become outdated.

An inference should not be treated as a validated fact.

CogniEDA should make provenance visible to the agent.

## Memory Should Know Freshness

Memory must have freshness or invalidation rules.

A memory item can become stale when:

- dataset version changes,
- source file hash changes,
- schema changes,
- metric definition changes,
- an assumption dependency is rejected,
- user overrides a definition,
- a preprocessing step changes,
- a branch is abandoned,
- a tool result expires,
- a commit changes,
- a time-based TTL expires.

Examples:

- A profile of `orders_v1` should not be treated as a profile of `orders_v2`.
- A validation result based on D7 retention becomes stale if retention is redefined as D30.
- A conclusion based on UTC timestamps becomes stale if timestamps are later found to be local time.
- A tool cache from an old file hash should not be reused for the current dataset.

Freshness is essential for trustworthy long-term reasoning.

## Controlled Forgetting

CogniEDA should implement controlled forgetting.

Forgetting does not mean deleting history.

It means deciding what should no longer be active.

Different actions have different meanings:

Delete:

Remove permanently.

Archive:

Keep for search, but exclude from active context.

Prune:

Remove from active context while preserving history.

Reject:

Mark as false or unsupported.

Stale:

Mark as no longer valid for current state.

Supersede:

Replace with a newer memory.

Dead-end:

Keep as a warning not to repeat.

Overrule:

Mark as explicitly replaced by user or evidence.

Controlled forgetting is as important as remembering.

An agent that remembers everything remembers too much.

An agent that forgets everything loses continuity.

CogniEDA should make the agent selectively remember.

## Pinned Memory

Pinned memory contains information that must stay active.

It should be small and high-value.

Examples of pinned memory for CogniEDA:

- DataProfile is not Evidence.
- Do not trust datasets without evidence.
- Every conclusion must trace to dataset version.
- Assumptions must be tracked and can become stale.
- Hypotheses require validation before becoming conclusions.
- Preprocessing creates assumptions.
- Correlation is not causation.
- Memory is context control, not just long-term storage.
- Rejected ideas should be remembered as warnings.
- User values evidence-based reasoning over confident speculation.
- The project focuses on deep data investigation and memory management.

Pinned memory should be protected from compaction and pruning.

But too much pinned memory becomes noise.

Pinning must be selective.

## Pruned Memory

Pruning removes information from active context without deleting it.

Useful candidates for pruning:

- resolved debugging detours,
- failed attempts,
- outdated reasoning paths,
- verbose tool outputs,
- repeated explanations,
- abandoned hypotheses,
- superseded decisions,
- irrelevant branches.

Pruned information can still be searched or restored.

The key idea:

The agent should not keep reasoning from content that the user has mentally discarded.

## Dead-End Memory

Dead ends should be preserved as warnings.

Examples:

- “Tried validating H4 using dataset v1, but target variable missingness made result invalid.”
- “Tried using row count as user count, but user confirmed each row is a session.”
- “Tried removing outliers, but the removed rows contained valid high-value customers.”
- “Tried joining on email, but email is not stable across accounts.”

Dead-end memory prevents repeated work.

But dead ends must not remain active as if they are viable directions.

They should influence reasoning only when the agent is about to repeat a failed path.

## Checkpoints

A checkpoint is a named reasoning state.

It is like a commit for context.

A checkpoint should capture:

- active dataset version,
- active assumptions,
- active hypotheses,
- current evidence,
- open questions,
- decisions,
- known risks,
- current branch,
- unresolved issues.

Examples:

- “before preprocessing”
- “after initial profiling”
- “before outlier removal”
- “after user confirmed metric definitions”
- “before validating retention hypotheses”
- “after rejecting customer_id uniqueness”

Restoring a checkpoint should not delete history.

It should restore the effective context to that state.

This allows the agent to backtrack without losing everything.

## Branching

Branching allows the agent to explore alternative analytical paths without contaminating the main reasoning thread.

Examples:

Main branch:

- Analyze churn using current retention definition.

Branch A:

- Define churn as no activity after 7 days.

Branch B:

- Define churn as no activity after 30 days.

Branch C:

- Exclude suspected bot traffic before computing churn.

Branch D:

- Keep bot traffic but segment by activity level.

Each branch may have its own assumptions, evidence, validation results, and conclusions.

Only validated or useful results should be merged back into the main context.

Branching prevents dead-end contamination.

It also supports experimentation.

## Tool Result Caching

Agents often repeat expensive lookups.

For coding agents, this may be:

- semantic search,
- codebase scan,
- dependency graph traversal,
- database schema lookup.

For CogniEDA, this may be:

- dataset profiling,
- missingness scan,
- duplicate check,
- correlation matrix,
- schema inference,
- column distribution analysis,
- validation result,
- expensive SQL query,
- external metadata lookup.

Tool results should be cacheable by topic and validity condition.

A cache entry should know:

- topic,
- dataset version,
- source hash,
- created time,
- method,
- summary,
- validity condition,
- expiration rule,
- related assumptions,
- related hypotheses.

Examples:

- “Profile cache for `orders_v2`, valid until file hash changes.”
- “Duplicate check for `customers_v1`, valid only for v1.”
- “Correlation matrix for `features_v3`, stale if preprocessing changes.”
- “Codebase scan for auth module, valid until commit SHA changes.”

Tool caching reduces repeated work, token waste, and inconsistent rediscovery.

But cached results must never be reused blindly.

They require freshness checks.

## Context Frames as Handoff Protocol

CogniEDA should support multiple agents without passing full conversation history.

Specialized agents may include:

- data profiling agent,
- data quality agent,
- hypothesis generation agent,
- validation agent,
- evidence review agent,
- memory distillation agent,
- reporting agent,
- code agent,
- research agent.

Each agent should receive only the context it needs.

A frame handoff should include:

- task goal,
- relevant dataset version,
- relevant assumptions,
- relevant hypotheses,
- evidence summary,
- known risks,
- open questions,
- tool cache references,
- required outputs,
- boundaries of responsibility.

No agent should need the full chat log of another agent.

A good handoff is compressed, structured, scoped, and provenance-aware.

## Memory Graph

CogniEDA should treat memory as a graph, not just a list.

Possible nodes:

- DataProfile,
- Evidence,
- Assumption,
- Hypothesis,
- ValidationResult,
- Conclusion,
- MetricDefinition,
- PreprocessingStep,
- ToolResult,
- UserDecision,
- ContextFrame,
- OpenQuestion,
- DeadEnd,
- CacheEntry.

Possible edges:

- supports,
- contradicts,
- depends_on,
- invalidates,
- supersedes,
- derived_from,
- generated_by,
- validated_on,
- applies_to,
- stale_when,
- used_by,
- handed_off_to,
- created_in,
- blocks,
- revalidates.

The memory graph allows dependency reasoning.

Examples:

- If assumption A2 is rejected, find all hypotheses depending on A2.
- If dataset v2 is invalidated, find all evidence generated on v2.
- If metric definition changes, find all conclusions using the old definition.
- If a preprocessing step is faulty, find all downstream dataset versions.
- If a conclusion is challenged, find its supporting evidence.
- If a tool cache is stale, prevent reuse.

Memory graph is what turns memory into reasoning infrastructure.

## Active Context vs Long-Term Memory

Long-term memory is the full knowledge store.

Active context is the small set of memory injected into the agent for the current task.

The agent should not load all long-term memory.

Before acting, the agent should ask:

- What is the current task?
- Which project is active?
- Which dataset version is active?
- Which hypotheses are relevant?
- Which assumptions are relevant?
- Which evidence is fresh?
- Which memory is stale?
- Which open questions block the task?
- Which rejected paths should be avoided?
- Which tool cache can be reused?

Memory retrieval is part of reasoning.

The agent should construct a minimal active context.

## Memory Conflict Handling

Long workflows create contradictions.

Example:

Old memory:

- “`price` is USD.”

New memory:

- “User confirmed `price` is VND.”

The system should not simply store both.

It should:

- detect conflict,
- mark old memory as overruled,
- link new memory as superseding old memory,
- update affected assumptions,
- mark affected hypotheses for review,
- downgrade conclusions if needed.

Another example:

Old assumption:

- “`created_at` is UTC.”

New evidence:

- “Timestamps match local Asia/Ho_Chi_Minh business hours and have no UTC marker.”

The old assumption may become risky or stale.

CogniEDA should prevent contradictory memory from silently coexisting as equal truth.

## Memory Should Store Why, Not Just What

Decisions without reasons are fragile.

Bad memory:

- “Removed duplicates.”

Better memory:

- “Removed duplicate rows by `order_id` because 351 repeated order IDs had identical payloads, suggesting ingestion duplication rather than valid repeat transactions.”

Bad memory:

- “Use D30 retention.”

Better memory:

- “Use D30 retention because user’s business goal is long-term customer return behavior, and D7 retention was too short for this product cycle.”

Bad memory:

- “Do not use correlation for marketing impact.”

Better memory:

- “Do not use correlation alone for marketing impact because campaign targeting may select users already likely to convert, creating confounding.”

Why helps future agents avoid reversing decisions incorrectly.

## Open Questions

Open questions should be first-class memory.

Examples:

- Is `created_at` UTC or local time?
- Does each row represent a user, session, order, or item?
- Is `customer_id` stable across accounts?
- Does missing `income` mean unknown or not applicable?
- Should retention be D7, D14, or D30?
- Was campaign targeting random?
- Is bot traffic present?
- Are refunds included in revenue?
- Does the dataset cover the full population?
- Was tracking changed during the analysis period?

Open questions prevent premature conclusions.

When a task touches an open question, the agent should surface it.

## Memory Analytics

CogniEDA should be able to measure context quality.

Useful metrics:

- memory hit rate,
- stale memory rate,
- repeated tool call rate,
- number of active assumptions,
- number of unvalidated assumptions,
- number of stale hypotheses,
- number of conclusions without evidence,
- number of unresolved open questions,
- dead-end ratio,
- cache reuse rate,
- context token waste,
- average frame size,
- evidence reuse rate,
- revalidation frequency,
- handoff completeness,
- context freshness.

These metrics help improve the system.

For example:

- High repeated tool call rate suggests weak caching.
- High stale memory rate suggests poor invalidation.
- Many conclusions without evidence suggest unsafe reasoning.
- Many active unvalidated assumptions suggest analytical risk.
- High dead-end ratio may indicate unclear task framing.
- Low memory hit rate suggests poor retrieval or memory quality.

CogniEDA should treat context as measurable.

## Automated Context Pipeline

At the end of a frame or session, CogniEDA should be able to run an automated memory pipeline.

The pipeline may:

- identify important decisions,
- extract assumptions,
- extract hypotheses,
- extract evidence,
- mark dead ends,
- prune irrelevant reasoning,
- cache reusable tool results,
- update memory graph,
- mark stale dependencies,
- produce handoff summary,
- list open questions,
- update active project memory,
- archive noisy details,
- keep only high-value memory active.

The pipeline should not blindly summarize.

It should preserve analytical structure.

Good memory extraction should answer:

- What changed?
- What was learned?
- What was rejected?
- What remains unresolved?
- What should future agents know?
- What should future agents avoid?
- What must be revalidated if conditions change?

## Memory for All Agents

Although CogniEDA focuses on data analysis, its memory ideas should apply to any agent.

Coding agent:

- remembers file decisions,
- caches code searches,
- tracks rejected implementation paths,
- links reasoning to commits,
- avoids repeating debugging dead ends.

EDA agent:

- tracks dataset versions,
- assumptions,
- hypotheses,
- evidence,
- validation results.

Research agent:

- tracks sources,
- claims,
- evidence strength,
- contradictions,
- stale information.

Planning agent:

- tracks decisions,
- constraints,
- milestones,
- blockers,
- changed priorities.

Review agent:

- tracks reviewed issues,
- accepted changes,
- rejected concerns,
- unresolved risks.

The common abstraction is context control.

Every agent needs to know:

- what is active,
- what is stale,
- what was rejected,
- what was decided,
- what is uncertain,
- what should be reused,
- what should be ignored,
- what should be handed off.

CogniEDA should aim to solve memory at this general level.

## Levels of Memory Capability

CogniEDA can think about memory maturity in levels.

Level 1: Surgical Context Control

The agent can pin, prune, mark resolved, mark dead-end, and mark overruled information.

Goal:

- reduce noise immediately.

Level 2: Checkpoints

The agent can save and restore reasoning states.

Goal:

- avoid nuclear reset and allow safe rollback.

Level 3: Context Frames

The agent can package work into bounded, named frames with goals, outcomes, evidence, decisions, open questions, and status.

Goal:

- turn chat into structured work product.

Level 4: Tool Result Caching

The agent can reuse expensive results by topic, dataset version, source hash, commit SHA, or TTL.

Goal:

- reduce repeated lookup waste.

Level 5: Versioned Memory Artifacts

The agent can persist memory artifacts alongside project history.

Goal:

- preserve reasoning across sessions and versions.

Level 6: Memory Graph

The agent can represent dependencies between datasets, assumptions, hypotheses, evidence, conclusions, decisions, and tool results.

Goal:

- support invalidation, impact analysis, and traceability.

Level 7: Automated Context Pipeline

The agent can automatically distill frames, prune noise, extract memory, update the graph, and prepare handoffs.

Goal:

- make memory maintenance scalable.

Level 8: Context Analytics

The system can measure memory quality, cache reuse, stale rate, dead-end rate, context freshness, and evidence coverage.

Goal:

- improve the agent’s long-term effectiveness.

Level 9: Branching and Merging

The agent can explore alternative reasoning paths without polluting the main context, then merge validated outcomes.

Goal:

- support experimentation without context contamination.

## CogniEDA’s Core Mental Model

CogniEDA should treat EDA as knowledge construction.

Raw data is not knowledge.

A chart is not knowledge.

A statistic is not knowledge.

A model result is not knowledge.

Knowledge emerges when observations are turned into evidence, evidence is linked to hypotheses, hypotheses are validated under assumptions, conclusions are assigned confidence, and everything remains traceable to dataset versions and memory state.

CogniEDA should transform:

raw data
→ observations
→ evidence
→ assumptions
→ hypotheses
→ validation results
→ insights
→ conclusions
→ memory
→ future active context.

The agent should constantly ask:

- What do we know?
- How do we know it?
- Which dataset version supports it?
- Which assumptions does it depend on?
- What could make it false?
- Is it still fresh?
- Is it strong enough to use?
- Should it be active, archived, stale, rejected, or pinned?

## Expected Agent Behavior

A CogniEDA agent should:

- avoid trusting data too early,
- distinguish dataset assets from evidence,
- track dataset versions,
- generate evidence before conclusions,
- make assumptions explicit,
- validate assumptions where possible,
- generate testable hypotheses,
- refine vague ideas into testable claims,
- validate hypotheses using suitable methods,
- mark results as supported, contradicted, inconclusive, or stale,
- avoid causal claims from correlation,
- treat preprocessing as assumption-generating,
- investigate missingness,
- handle outliers carefully,
- preserve rejected ideas as warnings,
- store open questions,
- manage memory actively,
- retrieve only relevant memory,
- mark stale memory,
- cache expensive tool results,
- support handoff between agents,
- reason through dependency graphs,
- and know when not to conclude.

The agent should not:

- produce unsupported insights,
- hide uncertainty,
- silently transform data,
- use stale evidence,
- confuse dataset versions,
- ignore rejected assumptions,
- treat memory as a raw chat log,
- summarize away important caveats,
- repeat expensive lookups unnecessarily,
- or let dead-end reasoning contaminate active context.

## Ultimate Goal

CogniEDA should become a framework for disciplined agentic reasoning over data and context.

It should make agents better not by giving them infinite memory, but by giving them structured, scoped, provenance-aware, freshness-aware, status-aware memory.

It should make EDA more trustworthy by requiring every important conclusion to be connected to evidence and dataset lineage.

It should make long-running agent workflows safer by preventing context rot.

It should make multi-agent workflows possible by turning session history into handoff-ready context frames.

It should make analytical work reproducible by tracking how data, assumptions, hypotheses, evidence, and conclusions evolve over time.

In one sentence:

CogniEDA is an agentic EDA and context-management system that turns messy, long-running data exploration into structured, evidence-based, version-aware, memory-controlled knowledge construction.

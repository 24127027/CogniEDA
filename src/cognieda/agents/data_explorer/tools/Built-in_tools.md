# Data Explorer — Built-in Tool Catalogue

**File:** `src/cognieda/agents/data_explorer/tools/Built-in_tools.md`  
**Status:** Authoritative tool inventory for the DE MVP  
**Last Updated:** 2026-08-13

---

## Overview

Every tool is a deterministic, side-effect-free Python function that operates on
a **deep copy** of the supplied DataFrame.  No tool mutates the source dataset.
Outputs are normalized to JSON-safe primitives before being returned to the
calling node.

Tools are grouped into `FunctionToolset` objects (Pydantic AI) and registered
with the DE model agent at construction time via `toolsets=[...]`.  All nodes
(planning, execute, check_result) share the same agent and therefore see all
toolsets.  The **instruction** passed to each `agent.run()` call governs which
operations each node is expected to invoke.

---

## Implementation Priority

| Priority | Toolset | Status |
|---|---|---|
| 1 | Dataset Profiling & Schema Inspection | **Implemented** (see `tools/profiling.py`) |
| 2 | Descriptive & Exploratory Analysis (EDA) | **Implemented** (see `tools/eda.py`) |
| 3 | Sandboxed Code Execution | **Implemented** (see `tools/sandbox.py`) |
| 4 | Statistical / Hypothesis Testing | **Intended — deferred post-MVP** |
| 5 | Bounded Data Transformations | **Intended — deferred post-MVP** |

---

## Toolset 1 — Dataset Profiling & Schema Inspection (`profiling_toolset`)

Backed by existing deterministic implementation in `analysis/profiling.py`.

| Tool name | Parameters | Return type | Description |
|---|---|---|---|
| `profile_dataset` | *(none — operates on bound df)* | `DataProfile` (JSON) | Full immutable typed profile: row count, column count, types, distinct/missing counts, continuous/discrete summaries. Does **not** drop rows or mutate input. |
| `inspect_schema` | *(none)* | `dict` | Returns column names, Pandas dtypes, inferred logical types (`CONTINUOUS`/`DISCRETE`) and nullable flags only — cheaper than a full profile. |
| `missingness_report` | `columns: list[str] \| None` | `dict` | Per-column missing count and ratio plus dataset-level complete-case row count. |
| `detect_duplicates` | `subset_columns: list[str] \| None` | `dict` | Total duplicate rows, duplicate ratio; returns top-3 duplicate index ranges for diagnostics. |

---

## Toolset 2 — Descriptive & Exploratory Analysis Tools (`eda_toolset`)

Wrappers around the deterministic helpers already present in `tools/analyze_dataset.py`.

| Tool name | Parameters | Return type | Description |
|---|---|---|---|
| `row_count` | *(none)* | `dict` | `{"row_count": int}` |
| `column_summary` | `column: str` | `dict` | dtype, count, missing_count, distinct_count |
| `value_counts` | `column: str`, `top_k: int` | `dict` | Frequency table for categorical/discrete series |
| `descriptive_statistics` | `column: str` | `dict` | min, max, mean, median, std, p25, p75 for numeric series |
| `distribution_histogram` | `column: str`, `bins: int = 10` | `dict` | Bin edges, bin counts, density (finite floats only) |
| `group_summary` | `group_by: str`, `value_column: str`, `max_groups: int`, `aggregations: list[str]` | `dict` | Mean/median/sum/std/count per group |
| `contingency_table` | `row_column: str`, `col_column: str`, `normalize: str \| None` | `dict` | Cross-tabulation with marginal sums |
| `correlation_matrix` | `columns: list[str]`, `method: str` | `dict` | Pearson / Spearman / Kendall matrix |
| `detect_outliers` | `column: str`, `method: str`, `threshold: float` | `dict` | Outlier count, ratio, cutoff bounds using IQR or Z-score |

---

## Toolset 3 — Sandboxed Code Execution (`sandbox_toolset`)

Handles tasks that cannot be served by a single builtin above.

| Tool name | Parameters | Return type | Description |
|---|---|---|---|
| `execute_code` | `code: str`, `target_columns: list[str]` | `dict` | Executes `code` against `df.copy(deep=True)` in a restricted environment. Captures `result` variable or last dict expression. Blocks `os`, `sys`, `subprocess`, `socket`, `open`. Raises `SandboxError` on timeout (15 s) or dangerous import. Returns `{"output": ..., "variables_accessed": [...], "values_observed": {...}}` |

---

## Toolset 4 — Statistical & Hypothesis Testing *(intended, deferred)*

Tools to be implemented when the `SCIENTIFIC` EvidenceRequest path is activated.

| Tool name | Notes |
|---|---|
| `two_sample_t_test` | Welch's t-test for two independent groups |
| `paired_t_test` | Paired observations before/after |
| `mann_whitney_u_test` | Non-parametric two-group comparison |
| `one_way_anova` | F-test across 3+ groups |
| `kruskal_wallis_test` | Non-parametric multi-group test |
| `chi_square_independence` | Categorical independence, Cramér's V |
| `linear_regression_univariate` | OLS, R², slope p-value |

---

## Toolset 5 — Bounded Data Transformations *(intended, deferred)*

To be implemented when successor-dataset creation and DataProfile lineage chains
are supported end-to-end.

| Tool name | Notes |
|---|---|
| `filter_rows` | Immutable filter → new dataset version + successor DataProfile |
| `impute_missing` | Mean/median/mode/constant → new dataset version + lineage record |
| `derive_column` | Append derived column → new dataset version |

---

## Agent & Toolset Integration Pattern

```python
from pydantic_ai import Agent, FunctionToolset

from cognieda.agents.data_explorer.tools import profiling_toolset
from cognieda.agents.data_explorer.tools import eda_toolset
from cognieda.agents.data_explorer.tools import sandbox_toolset

agent = agent_factory.create_agent(
    worker="data_explorer",
    config=model_config,
    deps_type=type(None),
    builtin_tools=(),
)

# At runtime, toolsets are injected per-call so the df context is bound:
result = await agent.run(
    prompt,
    output_type=PlanningOutput,
    instructions=planning_instructions,
    toolsets=[profiling_toolset(df), eda_toolset(df), sandbox_toolset(df)],
)
```

Each toolset factory accepts the deep-copied DataFrame so tools are stateless
and operate on the correct snapshot.

---

## Data Immutability Contract

Every tool function receives `df: pd.DataFrame` already isolated by the caller
(`df.copy(deep=True)` before dispatch).  No tool may reassign the original
frame reference, call `df.drop(inplace=True)`, or write to external storage.
This is verified by the `validate_profile_input_frame` guard already present in
`analysis/validation.py`.

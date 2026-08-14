---
type: Workflow Guide
title: CogniEDA Common Workflows
description: Step-by-step guides for common tasks including creating objectives, running analysis, evaluating hypotheses, and resuming sessions.
tags: [workflows, how-to, tutorial, recipes]
---

# Common Workflows

## Workflow 1: Basic Analysis from Scratch

### Objective
Analyze a dataset to understand relationships and validate hypotheses.

### Steps

#### 1. Create Workspace

```powershell
mkdir my_analysis
cd my_analysis
cognieda .
```

This initializes `.cognieda/` directory with local configuration and database.

#### 2. Define Objective

In the REPL:
```
> objective "Identify factors influencing customer retention"
Created Objective obj-001
Intent: Identify factors influencing customer retention
Scope: (default - full workspace)
```

**What happens**:
- Human authority creates Objective
- Persisted to database
- Becomes active context

#### 3. Load Data

```
> load data/customers.csv
Loaded: data/customers.csv
Profiling dataset...
Created DataProfile prof-284
  Columns: 12
  Rows: 100,000
  Missing values: 342 (0.3%)
```

**What happens**:
- Data Explorer profiles dataset
- DataProfile immutable snapshot created
- Eligible for analysis

#### 4. Generate Hypotheses

```
> hypothesize
Analyzing objective and data...
Generated 5 hypotheses:

hyp-1: Monthly churn correlates with email engagement
hyp-2: Premium tier has lower churn than standard
hyp-3: Geographic region affects retention rates
hyp-4: Customer support interactions reduce churn
hyp-5: Account age predicts retention likelihood

Review and approve?
```

**What happens**:
- Hypothesis Analyst generates claims
- Based on objective and available data
- Proposed to human for approval

#### 5. Approve Plan

```
> approve hyp-1 hyp-2 hyp-4
Approved 3 hypotheses
Planning tasks...
Generated 8 tasks:

task-1: Extract email engagement metrics
task-2: Calculate churn rates by tier
task-3: Validate tier effect with statistical test
task-4: Collect support interaction counts
task-5: Analyze support impact on retention
...

Execute tasks?
```

**What happens**:
- Planner creates Task DAG
- Tasks have dependencies
- Ready for execution

#### 6. Run Analysis

```
> execute
Executing 8 tasks...

[task-1] Extract engagement metrics... ✓ (2.3s)
[task-2] Calculate churn by tier... ✓ (1.8s)
[task-3] Statistical validation... ✓ (5.2s)
Generated Evidence evd-156: p-value=0.0001, correlation=0.72

[task-4] Collect support data... ✓ (1.5s)
[task-5] Analyze support impact... ✓ (3.1s)
Generated Evidence evd-158: support interactions reduce churn by 35%

(more tasks...)

Execution complete. 5 evidence records created.
Ready to evaluate?
```

**What happens**:
- Execution Dispatcher routes tasks
- Specialists run analysis
- Evidence recorded with provenance
- Results ready for evaluation

#### 7. Evaluate Evidence

```
> evaluate
Comparing hypotheses against evidence...

hyp-1: Email engagement hypothesis
  Evidence evd-156: correlation=0.72, p-value=0.0001
  Evaluation: STRONG SUPPORT
  Confidence: 0.92

hyp-2: Premium tier hypothesis
  Evidence evd-157: tier effect=35% retention lift
  Evaluation: CONFIRMED
  Confidence: 0.88

hyp-4: Support interaction hypothesis
  Evidence evd-158: support reduces churn by 35%
  Evaluation: CONFIRMED
  Confidence: 0.85

Admit as discoveries?
```

**What happens**:
- Scientific authority evaluates
- Compares hypotheses to evidence
- Judges fit and confidence
- Ready for admission

#### 8. Admit Discoveries

```
> admit hyp-1 hyp-2 hyp-4
Admitted 3 discoveries:

disc-089: Email engagement strongly correlates with retention
disc-090: Premium tier customers retain at 35% higher rate
disc-091: Customer support interactions reduce churn by 35%

Available for future analysis and reporting.
```

**What happens**:
- Discovery authority admits claims
- Become eligible for future reference
- Can be used in subsequent objectives
- Fully audited and traceable

### State at Completion

```
Research State:
- 1 Objective (completed)
- 3 Discoveries (admitted)
- 5 Evidence records (validated)
- 1 DataProfile (immutable snapshot)
```

---

## Workflow 2: Multi-Session Analysis with Resume

### Objective
Conduct analysis across multiple sessions, preserving context.

### Session 1: Initial Exploration

```
> objective "Explore customer lifetime value drivers"
> load data/transactions_2024.csv
> hypothesize
Generated 4 hypotheses
> approve hyp-1 hyp-2
> execute
Generated 3 evidence records
> (pause - need to think about next steps)
```

#### Save Session

```
> checkpoint "Initial exploration complete; ready for cohort analysis"
Created SessionFrame frame-007:
  Active objective: obj-002
  Eligible evidence: 3 records
  Eligible discoveries: 2 records
  Created: 2026-08-14T14:30:00Z
  
Current context saved. Safe to close REPL.
```

**What happens**:
- SessionFrame created
- Captures current objective, evidence, discoveries
- Immutable snapshot
- Enables safe context switch

### Session 2: Resume and Continue

```
> resume frame-007
Loaded SessionFrame frame-007:
  Objective: "Explore customer lifetime value drivers"
  Available evidence: 3 records
  Available discoveries: 2 records
  Prior work: Initial exploration complete; ready for cohort analysis

Continue analysis?
```

**What happens**:
- Context authority restores SessionFrame
- Prior objectives, evidence, discoveries available
- Ready to continue where you left off

```
> hypothesize
Analyzing updated objective and new data...
Generated 2 new hypotheses based on prior evidence:

hyp-5: High-value cohorts emerge after 6-month engagement
hyp-6: Renewal rate predicts lifetime value

> approve hyp-5 hyp-6
> execute
Generated 2 more evidence records
```

#### Update Checkpoint

```
> checkpoint "Cohort analysis complete; ready for prediction modeling"
Updated SessionFrame frame-007
  Evidence: 5 records
  Discoveries: 3 records
```

### State Across Sessions

```
Session 1:
  Created: 3 evidence
  Discoveries: 2

Session 2:
  Created: 2 evidence
  Discoveries: 1 (new)

Total (preserved across sessions):
  Evidence: 5
  Discoveries: 3
  All lineage preserved
```

**Key benefit**: Full context restored without starting over or losing prior findings.

---

## Workflow 3: Collaborative Analysis

### Setup

Team member A and team member B work on same objective.

```
Team A                          Team B
├── workspace/                  ├── workspace/
│   ├── obj-003                 │   ├── obj-003 (same)
│   ├── data/                   │   ├── data/ (same)
│   └── discoveries/            │   └── discoveries/
```

### Execution

#### Team A: Task 1

```
cognieda workspace/
> objective "Analyze regional differences"
> load data/regional_data.csv
> hypothesize
> approve hyp-1 hyp-2
> execute (runs tasks 1-4)
> checkpoint "Regional analysis done"
```

Created: disc-100, disc-101

#### Team B: Task 2 (in parallel)

```
cognieda workspace/
> resume latest
> hypothesize (generates new hypotheses based on disc-100, disc-101)
> approve hyp-5 hyp-6
> execute (runs tasks 5-8)
> checkpoint "Demographic analysis done"
```

Created: disc-102, disc-103

#### Team Consolidation

```
> show discoveries
Available discoveries:
  disc-100: Regional effect found (Team A)
  disc-101: Regional pattern (Team A)
  disc-102: Demographic correlation (Team B)
  disc-103: Demographic interaction (Team B)

All results integrated into objective.
```

**Key properties**:
- Shared workspace database
- SessionFrames ensure context safety
- No merge conflicts (immutable state)
- Full lineage preserved

---

## Workflow 4: Hypothesis Refinement

### Objective
Start with broad hypothesis, refine based on evidence.

### Step 1: Initial Hypothesis

```
> hypothesis "Customer engagement drives retention"
Created hyp-10
```

**Authority**: Human + Specialist generate
**State**: PROPOSED

### Step 2: Test Against Data

```
> execute
Generated evidence evd-200: correlation=0.45, weak
```

**Authority**: Execution records
**State**: Evidence recorded

### Step 3: Evaluate

```
> evaluate hyp-10 against evd-200
Evaluation: WEAK SUPPORT (correlation too weak to confirm)
Suggest refinement?
```

**Authority**: Scientific judges fit
**State**: PROVISIONAL (needs refinement)

### Step 4: Refine

```
> refine hyp-10 "High-engagement customers (>90th percentile) have 2x retention"
Created hyp-11 (refined from hyp-10)
```

**Authority**: Human authority refines
**State**: New hypothesis created

### Step 5: Re-test

```
> execute (re-run analysis with new definition)
Generated evidence evd-201: correlation=0.82, strong
```

**Authority**: Execution records
**State**: New evidence

### Step 6: Admit

```
> evaluate hyp-11 against evd-201
Evaluation: STRONG SUPPORT
> admit hyp-11
Admitted disc-110: High-engagement customers have 2x retention
```

**Authority**: Discovery authority
**State**: DISCOVERED (fully evaluated and admitted)

### Result

```
Refinement chain:
hyp-10 (weak) → evd-200 (weak correlation)
  ↓ (refined)
hyp-11 (strong) → evd-201 (strong correlation)
  ↓ (admitted)
disc-110 (discovery)

Full lineage preserved for audit.
```

---

## Workflow 5: Data Validation and Profiling

### Objective
Ensure data quality before analysis.

```
> load data/raw_data.csv
Profiling dataset...
Created DataProfile prof-285

Profile summary:
  Rows: 50,000
  Columns: 15
  Completeness:
    - customer_id: 100%
    - email: 99.2%
    - purchase_date: 98.5%
    - amount: 87.3% (missing: 6,245)
  Data types:
    - customer_id: string
    - purchase_date: datetime
    - amount: float
```

### Validate Against Contract

```
> validate
Checking against schema...

✓ customer_id: non-null, unique
✓ purchase_date: valid datetime
✓ amount: positive numeric
✗ email: 0.8% null (contract requires 99.5%)

Validation failed. Review data quality issue?
```

### Decision

**Option 1: Proceed with imputation**
```
> impute email (strategy: forward-fill)
Imputed 496 missing values
Re-profiled dataset
Profile valid for analysis
```

**Option 2: Filter records**
```
> filter "email IS NOT NULL"
Filtered to 49,504 rows (0.8% removed)
Re-profiled dataset
Profile valid for analysis
```

**Option 3: Halt and investigate**
```
> investigate email
Email column analysis:
  - Missing pattern: concentrated in legacy users
  - Recommendation: Create separate cohort or impute

Decision: Create separate analysis for legacy segment
```

### Result

```
DataProfile now valid for analysis:
  prof-285 (after validation)
  Eligible for hypothesis testing
  Evidence will reference this profile
```

---

## Quick Reference: Command Patterns

### Objective Operations
```
objective "description"        Create objective
show objectives               List all objectives
set objective <id>            Set active objective
```

### Data Operations
```
load <path>                   Load and profile data
show data                     Show current DataProfile
validate                      Check data against schema
impute <column>              Fill missing values
filter <condition>           Filter rows
```

### Hypothesis Operations
```
hypothesize                   Generate hypotheses
approve <id> [<id> ...]      Approve hypotheses
show hypotheses               List hypotheses
refine <id> "<new claim>"     Refine hypothesis
```

### Execution Operations
```
execute                       Run tasks for approved hypotheses
show tasks                    List task DAG
show evidence                 List evidence records
```

### Evaluation Operations
```
evaluate                      Judge hypothesis-evidence fit
evaluate <hyp> against <evd>  Evaluate specific pair
show evaluations              List all evaluations
```

### Discovery Operations
```
admit <id> [<id> ...]        Admit discoveries
show discoveries              List admitted discoveries
retract <id>                 Retract discovery
```

### Session Operations
```
checkpoint "<message>"        Save session context
resume <frame-id>            Restore session
show frames                   List saved sessions
```

---

## Troubleshooting Workflows

### Problem: "Cannot execute without approved hypotheses"

**Cause**: No hypotheses approved  
**Solution**:
```
> hypothesize
> approve <id>
> execute
```

### Problem: "Evidence invalid - source data changed"

**Cause**: DataProfile superseded  
**Solution**:
```
> load data/updated_data.csv
> show evidence
(Evidence now shows as PROVISIONAL)
> execute (re-run analysis)
> (Generate new evidence)
```

### Problem: "Cannot admit discovery - insufficient evidence"

**Cause**: Evaluation confidence too low  
**Solution**:
```
> gather more data or refine hypothesis
> execute (new analysis)
> evaluate (check confidence increased)
> admit
```

### Problem: "Session context lost"

**Cause**: Didn't save SessionFrame  
**Solution**: Always checkpoint before leaving:
```
> checkpoint "Work in progress"
> (REPL closes safely)
> resume (frame-id)
```


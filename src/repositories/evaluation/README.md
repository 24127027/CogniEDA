# Evaluation Control Repository (`repositories.evaluation`)

## Purpose
`repositories.evaluation` owns persistence access for non-FCO `EvaluationControlRecord` database entities.

## Modules
- `control.py`: `EvaluationControlRepository` and `ACTIVE_EVALUATION_STATES`.

## Responsibilities
- Primary key lookup, evaluation key lookup, and hypothesis active-evaluation query.
- Staging creation of control records within a database session.

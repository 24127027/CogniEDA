# Development & Collaboration Guidelines

This document outlines the standard practices for collaborating on this repository. Adhering to these guidelines ensures a clean codebase, efficient reviews, and smooth teamwork.

## 1. Branch Management and Workflow

*   **Every branch should be main-based:** Always branch off from the `main` branch when starting new work.
    *   *Reason:* Ensures you build on the most stable, up-to-date codebase, minimizing complex merge conflicts.
*   **Delete branches after merge:** Create a new branch for your work and delete it once merged.
    *   *Reason:* Keeps the repository clean and prevents others from basing work on stale branches.
*   **Keep PRs focused:** Restrict every Pull Request to a single feature or a single fix.
    *   *Reason:* Makes reviews faster and easier, and simplifies reverting if a specific change breaks production.
*   **No cross-merging:** Cross-merging between active feature branches is strictly prohibited.
    *   *Reason:* Prevents tangled commit histories and stops incomplete code from sneaking into deployments.
*   **Dependent branches:** Allow dependent branches *only* when a feature explicitly depends on another unfinished feature.
    *   *Reason:* A controlled exception to the cross-merging rule, allowing progress without being blocked.

## 2. Branch Naming Convention

Branches must start with a prefix indicating the reason for the branch:

*   `feature/` - for developing a new feature (e.g., `feature/agent-definition`)
*   `fix/` - for fixing a bug or issue
*   `refactor/` - for restructuring code without changing external behavior

## 3. Code Naming Convention

Strictly adhere to the following naming conventions across the codebase:

*   **Files, variables:** `snake_case`
*   **Constants:** `SCREAMING_SNAKE_CASE`
*   **Classes:** `PascalCase`

## 4. Pull Request Message Structure

To outline what changed and make reviews easier, use the following structured template `docs/development/pull_request_template.md` in the repository.

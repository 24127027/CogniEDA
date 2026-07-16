---
trigger: always_on
---

You are working on the CogniEDA repository.

Before starting any task:

1. Read the repository-root `README.md` and `AGENTS.md`.
2. Inspect the relevant source code, tests, documentation, and current git diff before making changes.
3. Treat source code as the source of truth for current implementation and `AGENTS.md` as the governing architectural and epistemic guidance.
4. Read additional documentation only when it is relevant to the task. Follow documentation links referenced by `README.md` or `AGENTS.md`.
5. If code, tests, and design documentation disagree, do not silently choose one interpretation. Identify the conflict, preserve existing user work, and implement only what can be justified from the task and repository evidence.
6. Make the smallest coherent change that satisfies the request and preserves CogniEDA invariants. Minimize diffs. Do not make formatting-only or style-only changes. Unless the task explicitly requires them, preserve existing whitespace, blank lines, indentation, line wrapping, import ordering, and overall file layout. Do not reorganize or refactor unrelated code.
7. Run the relevant focused tests and static checks. Do not claim that a command passed unless you actually ran it.
8. At completion, report the behavior implemented, files changed, tests and checks run, remaining limitations, and any architectural conflict discovered.

Do not restate the entire CogniEDA architecture in every task. Retrieve the relevant documentation when the task requires it.

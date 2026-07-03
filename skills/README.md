# Skills Specification

This directory contains the skill definitions used by CogniEDA agents.

Skills are written as `SKILL.md` files and loaded dynamically by `pydantic_ai_skills`. They provide reusable, context-aware instructions and domain-specific guidance to agents without requiring alterations to the core application prompts.

## Directory Structure

Skills are organized hierarchically. To prevent namespace collisions during discovery, **group directories must only contain subdirectories**. Broad or generic instructions should be isolated into a `core/` or `general/` folder.

```
skills/
├── planner/
│   ├── core/                    # Broad/generic planning rules
│   │   └── SKILL.md
│   ├── task-planning/           # Child skill
│   │   └── SKILL.md
│   └── execution/               # Child skill
│       └── SKILL.md
└── statistics/
    ├── core/                    # Broad/generic statistical rules
    │   └── SKILL.md
    ├── correlation/             # Child skill
    │   └── SKILL.md
    └── hypothesis-testing/      # Child skill
        └── SKILL.md
```

Each leaf directory represents exactly one discrete skill and must contain a single `SKILL.md` file.

## Frontmatter Requirements

Every `SKILL.md` file **must** begin with a valid YAML frontmatter block. The registry indexes, discovers, and exposes skills to agents based entirely on this metadata block rather than file names or parent folder names.

```markdown
---
name: task-planning
description: Guidelines for decomposing broad goals into chronologically sound milestones and concrete tasks.
---
# Task Planning Architecture
1. Analyze upstream system parameters...
```

- **`name`**: A unique string identification tag used for registry mapping and tool calls.
- **`description`**: A concise, semantic summary detailing *when* and *why* an agent should dynamically invoke this skill.

## Skill Hierarchy & Inheritance

Skills are loaded recursively. Enabling a top-level capability group directory automatically includes all nested descendant skills down the directory tree.

For example, initializing:

```toml
directories = ["./skills/planner"]
```

automatically registers and exposes the following skill set to the runtime capability layer:

- `planner/core`
- `planner/task-planning`
- `planner/execution`

This allows broad application capabilities to be cleanly composed from smaller, highly focused skill modules.

## Configuration

Skills are configured in `config/skills.toml` and assigned to agents via `config/agents.toml`.

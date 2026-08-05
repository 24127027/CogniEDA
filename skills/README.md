# Skills package guidance

This directory is the intended location for CogniEDA skill definitions. It
currently contains no `SKILL.md` implementations.

The source includes a `pydantic_ai_skills` loader and `ToolManager` selection
seam, while `config/skills.toml` points to skill directories that are absent
from the current tree. This is **Partially implemented** assembly plumbing, not
proof that a composed runtime loads or applies the configured skills.

## Directory Structure

Future skills should be organized hierarchically. To prevent namespace
collisions during discovery, **group directories must only contain
subdirectories**. Broad or generic instructions should be isolated into a
`core/` or `general/` folder.

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

Each future leaf directory represents exactly one discrete skill and must
contain a single `SKILL.md` file.

## Frontmatter Requirements

Every future `SKILL.md` file **must** begin with a valid YAML frontmatter block.
The underlying skills library uses this metadata during discovery; repository
configuration alone does not establish agent use.

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

The intended hierarchy relies on recursive loading by the skills library.
Enabling a top-level capability group directory is expected to include nested
descendant skills down the directory tree, subject to library validation and
an actual composed caller.

For example, initializing:

```toml
directories = ["./skills/planner"]
```

would expose the following skill set to that configured capability:

- `planner/core`
- `planner/task-planning`
- `planner/execution`

This allows broad application capabilities to be cleanly composed from smaller, highly focused skill modules.

## Configuration

Skills are declared in `config/skills.toml` and assigned by name in
`config/agents.toml`. The referenced directories do not currently exist, and
there is no supported end-to-end agent runtime. See
[Current state](../docs/status/current-state.md) for the verified boundary.

---
okf_version: "0.1"
---

# CogniEDA Wiki

Welcome to the CogniEDA wiki. This is the authoritative knowledge base for CogniEDA validity-preserving research-state infrastructure.

## Quick Navigation

### Getting Started

- **[Quick Start](./quickstart.md)** - Set up and launch CogniEDA in 5 minutes
- **[System Overview](./overview.md)** - High-level architecture and core concepts
- **[Current Status](./status/current-state.md)** - What's implemented, limitations, roadmap

### Understanding CogniEDA

- **[Research State Concepts](./concepts/research-state.md)** - Eight FCOs, authority model, validity
- **[Architecture Deep Dive](./architecture/deep-dive.md)** - Three-plane design, data flows, extension points
- **[Component Reference](./reference/components.md)** - CLI, classes, schemas, configuration

### Development

- **[Development Setup](./development/setup.md)** - Dev environment, testing, contribution workflow

---

## By Role

### Researchers & Analysts

1. Start with [Quick Start](./quickstart.md)
2. Learn [Research State Concepts](./concepts/research-state.md)
3. Follow [System Overview](./overview.md)
4. Reference [Component Reference](./reference/components.md)

**Time commitment**: 1-2 hours

### Software Engineers

1. Start with [Development Setup](./development/setup.md)
2. Read [Architecture Deep Dive](./architecture/deep-dive.md)
3. Review [Component Reference](./reference/components.md)
4. Explore source code in `src/cognieda/`

**Time commitment**: 2-4 hours

### Architects & Reviewers

1. Start with [System Overview](./overview.md)
2. Deep dive into [Architecture Deep Dive](./architecture/deep-dive.md)
3. Review [Research State Concepts](./concepts/research-state.md)
4. Check [Current Status](./status/current-state.md) for boundaries

**Time commitment**: 2-3 hours

### Project Owners

1. [System Overview](./overview.md) - High-level design
2. [Current Status](./status/current-state.md) - What works, what's deferred
3. [Development Setup](./development/setup.md) - Team onboarding

**Time commitment**: 30-45 minutes

---

## Key Concepts at a Glance

### Eight First-Class Objects (FCOs)

CogniEDA governs eight types of research state with distinct lifecycles and authorities:

**Semantic Knowledge Graph**:
- **Objective** - Research intent (human authority)
- **Hypothesis** - Testable claim (specialist generates, human approves)
- **Evidence** - Observed result (execution records, scientific evaluates)
- **Discovery** - Admitted claim (scientific + discovery authority)

**Supporting Objects**:
- **DataProfile** - Dataset snapshot (immutable metadata)
- **Assumption** - Planning-only statement (cannot become fact without evidence)
- **Task** - Semantic work unit (planner creates, execution runs)
- **SessionFrame** - Context bookmark (enables safe multi-session resume)

### Eight Authorities

Each authority owns specific state transitions. No authority can bypass another:

1. **Human** - Sets research intent and approves plans
2. **Planner** - Coordinates objectives and generates tasks
3. **Data Admission** - Validates dataset eligibility
4. **Execution** - Runs work and reports completion
5. **Evidence** - Records observed results
6. **Scientific** - Judges hypothesis-evidence fit
7. **Discovery** - Admits final claims
8. **Context** - Governs session scope and resume

### Three-Plane Architecture

```
Authority Plane       → Human decisions, scientific judgment
Control Plane         → Planning, coordination, admission
Specialist Plane      → Data exploration, analysis, execution
```

### Key Properties

- **Immutability**: Research state is append-only; changes create versions
- **Type Safety**: Different reasoning modes use different data types
- **Traceability**: Full lineage from question to conclusion
- **Validity Propagation**: Invalidity cascades appropriately
- **Multi-session Resume**: Explicit SessionFrames bookmark context

---

## Implementation Status

**MVP Foundation**: ✓ Complete

What works:
- Research state model and persistence
- Authority boundaries and transitions
- Specialist agents (Planner, Data Explorer, Hypothesis Analyst, Graph Miner)
- CLI and REPL interface
- Multi-provider LLM support
- Configuration system

What's deferred:
- End-to-end application server
- Orchestration layer (multi-step workflows)
- UI and visualization
- Production deployment
- Scaling infrastructure

See [Current Status](./status/current-state.md) for detailed capability boundaries and roadmap.

---

## Documentation Organization

```
openwiki/
├── index.md                        (this file)
├── overview.md                     System overview
├── quickstart.md                   Getting started
├── concepts/
│   └── research-state.md           FCOs and authority model
├── architecture/
│   └── deep-dive.md                Technical architecture
├── reference/
│   └── components.md               API and CLI reference
├── status/
│   └── current-state.md            Implementation status
└── development/
    └── setup.md                    Dev environment & contribution
```

---

## FAQ

**Q: What is CogniEDA?**  
A: Research-state infrastructure that keeps investigation intent, data, assumptions, observations, claims, and validity distinct and traceable.

**Q: Why do I need it?**  
A: Because conversations blur planning ideas, assumptions, and proven facts. CogniEDA makes research state explicit and auditable.

**Q: Is it a chatbot?**  
A: No. It's infrastructure for analytical investigation. It has agents, but they're specialists, not replacements for human judgment.

**Q: Can I use it for my research?**  
A: Yes, if you need to:
- Keep research state explicit and traceable
- Resume analysis across sessions safely
- Track full provenance of claims
- Validate findings against evidence
- Collaborate with traceable state

**Q: Is it production-ready?**  
A: MVP foundation is stable. End-to-end application packaging is deferred. See [Current Status](./status/current-state.md).

**Q: How do I get started?**  
A: Follow [Quick Start](./quickstart.md) (5 minutes), then read [System Overview](./overview.md).

**Q: Where can I ask questions?**  
A: Check [Discussions](https://github.com/your-org/CogniEDA/discussions) or file an [Issue](https://github.com/your-org/CogniEDA/issues).

---

## Contributing

This wiki is maintained alongside the code. Contributions welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes (in `/openwiki`)
4. Ensure OKF front matter compliance
5. Submit pull request

See [Development Setup](./development/setup.md) for details.

---

## License

CogniEDA is open source under the [LICENSE](../LICENSE) included in the repository.

---

**Last updated**: 2026-08-14  
**Status**: MVP Foundation Complete

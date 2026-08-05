# Application package

The application package is a **Partially implemented** application-authority
foundation, not a composed request runtime.

Current code under `orchestrator/` provides bounded Planner-operation commit,
execution admission/outbox creation, and execution-attempt transitions. The
`bootstrap/` and `events/` directories contain documentation only. There is no
root runtime object, request pipeline, response pipeline, service adapter, or
event bus.

The canonical application-authority boundary owns validation, admission,
persistence, transactions, validity transitions, and operational safety; it
does not author planning or scientific content. See
[Persistence and admission](../../docs/architecture/persistence-and-admission.md)
and [Current state](../../docs/status/current-state.md).

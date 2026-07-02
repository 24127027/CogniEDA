# Events

The `events` package provides the application's internal event system.

Events allow independent components to react to changes in application state without introducing direct dependencies. They communicate that **something has already happened**, enabling side effects to remain decoupled from the primary execution flow.

The event system **does not contain business logic or research reasoning**. It only transports notifications between components.

## Responsibilities

The events package is responsible for:

- Defining event types
- Publishing runtime events
- Registering event handlers
- Delivering events to subscribers
- Coordinating event-driven side effects

In short, it answers the question:

> **How do components react to runtime events?**

## Responsibilities that do NOT belong here

The events package should never contain:

- research planning
- workflow orchestration
- domain reasoning
- executor implementation
- persistence logic

Event handlers should react to events rather than determine application behavior.

## Typical Event Flow

```
Component
     │
     ▼
Publish Event
     │
     ▼
Event Bus
     │
     ├── Handler A
     ├── Handler B
     └── Handler C
```

Publishers remain unaware of which handlers receive an event.

## Design Principles

- Event-driven communication
- Loose coupling
- Immutable event payloads
- Multiple subscribers
- Side-effect isolation

## Relationship to Other Packages

```
events
    │
    ├── application
    ├── execution
    └── persistence
```

The event system coordinates notifications between packages without coupling them directly.

## Package Structure

```
events/
    event_bus.py
    event_handlers.py
    event_types.py
```

- `event_types.py` defines application event models.
- `event_bus.py` publishes and delivers events.
- `event_handlers.py` implements reactions to published events.
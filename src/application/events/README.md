# Events

The `events` package provides the application's internal event system.

It enables independent components to react to completed operations without introducing direct dependencies. Events represent facts that have already occurred and allow side effects to be handled outside the primary request execution flow.

## Responsibilities

The events package is responsible for:

- Defining application event types
- Publishing runtime events
- Registering event handlers
- Delivering events to subscribers
- Coordinating event-driven side effects

In short, it answers the question:

> **How do application components react to completed runtime events?**

## Typical Event Flow

```
Application
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

Publishers remain unaware of which handlers receive an event, allowing components to evolve independently.

## Design Principles

- Event-driven communication
- Loose coupling
- Immutable event payloads
- Multiple independent subscribers
- Side-effect isolation

## Package Structure

```
events/
    event_bus.py
    event_handlers.py
    event_types.py
```

- `event_types.py` defines application event models.
- `event_bus.py` publishes events and delivers them to subscribers.
- `event_handlers.py` implements side effects triggered by published events.
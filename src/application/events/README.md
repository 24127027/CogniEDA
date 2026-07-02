# Events

The `events` package provides the application's internal event system.

It enables independent components to react to changes in application state without introducing direct dependencies. Events represent facts that have already occurred, allowing side effects to be handled outside the primary request execution flow.

The event system does **not** coordinate request execution or perform research reasoning. Its responsibility is to propagate notifications so interested components can react independently.

## Responsibilities

The events package is responsible for:

- Defining application event types
- Publishing runtime events
- Registering event handlers
- Delivering events to subscribers
- Coordinating event-driven side effects

In short, it answers the question:

> **How do application components react to completed runtime events?**

## Responsibilities that do NOT belong here

The events package should never contain:

- request orchestration
- workflow planning
- research reasoning
- executor implementation
- task decomposition

Event handlers may implement application side effects, but they should never control the primary execution flow.

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

## Events vs Commands

Events represent completed facts rather than requests.

Publishing an event does not imply that any subscriber exists or that a particular action will occur. Components publish events without knowledge of who, if anyone, will react.

For example:

```
DiscoveryCreated
      │
      ├── Update search index
      ├── Persist audit log
      └── Notify interested services
```

The publisher is unaware of these side effects.

## Design Principles

- Event-driven communication
- Loose coupling
- Immutable event payloads
- Multiple independent subscribers
- Side-effect isolation
- No control over primary execution flow

## Relationship to Other Packages

```
application
      │
      ▼
events
      │
      ├── persistence
      ├── indexing
      ├── logging
      └── notifications
```

Application components publish events. Independent subscribers react to them without introducing direct dependencies between packages.

## Package Structure

```
events/
    event_bus.py
    event_handlers.py
    event_types.py
```

- `event_types.py` defines the application's event models.
- `event_bus.py` publishes events and delivers them to registered subscribers.
- `event_handlers.py` implements side effects triggered by published events.
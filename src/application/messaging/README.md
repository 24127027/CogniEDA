# Messaging

The `messaging` package defines the message contracts used for communication between runtime components.

Unlike events, which describe completed actions, messages represent requests and responses exchanged during an active workflow. They provide a stable communication protocol without introducing direct dependencies between components.

The messaging package contains only communication models. It does not implement transport or execution logic.

## Responsibilities

The messaging package is responsible for:

- Defining request messages
- Defining response messages
- Standardizing communication models
- Providing shared message contracts

In short, it answers the question:

> **How do runtime components exchange structured information?**

## Responsibilities that do NOT belong here

The messaging package should never contain:

- business logic
- planner logic
- executor implementation
- event dispatching
- transport implementation

Messages are communication contracts, not executable behavior.

## Typical Message Flow

```
Component A
      │
      ▼
Request Message
      │
      ▼
Component B
      │
      ▼
Response Message
      │
      ▼
Component A
```

Unlike events, messages are exchanged between known participants and usually expect a response.

## Design Principles

- Explicit communication contracts
- Immutable message models
- Transport-independent
- Strong typing
- No business logic

## Relationship to Other Packages

```
messaging
    │
    ├── application
    ├── execution
    ├── agents
    └── events
```

The messaging package provides common communication models shared across the application.

## Package Structure

```
messaging/
    request_pipeline.py
    response_pipeline.py
```

- `request_pipeline.py` defines the flow of inbound application requests.
- `response_pipeline.py` defines the flow of outbound application responses.
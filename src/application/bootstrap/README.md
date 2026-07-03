# Bootstrap

The `bootstrap` package initializes the CogniEDA application.

It assembles the application's runtime environment by constructing shared infrastructure, registering implementations, and wiring dependencies before the application begins processing requests.

Bootstrap executes only during application startup.

## Responsibilities

The bootstrap package is responsible for:

- Constructing application services
- Registering implementations
- Initializing shared infrastructure
- Wiring runtime dependencies
- Producing the application's root runtime object

In short, it answers the question:

> **How is the application assembled before it starts?**

## Typical Startup Flow

```
Application Start
        │
        ▼
Bootstrap
        │
        ├── Create infrastructure
        ├── Register services
        ├── Wire dependencies
        └── Return application instance
```

After startup completes, the initialized runtime is used to process all application requests.

## Design Principles

- Single startup responsibility
- Dependency injection
- Explicit configuration
- Immutable application wiring

## Package Structure

```
bootstrap/
    dependency_container.py
```

- `dependency_container.py` creates, configures, and wires application components.
# Dependency Direction

## Rules

1. Core interfaces do not import provider SDKs.
2. Adapters depend on core interfaces.
3. Projects depend on infrastructure contracts.
4. Temporary providers never become mandatory project dependencies.
5. Runtime adapters translate native runtime semantics into the standard Runtime contract.
6. Tool implementations do not assume one agent runtime.
7. Model providers are accessed through the Model Gateway.
8. Persistent state is accessed through state abstractions.
9. Secrets are accessed through secret abstractions.
10. External side effects pass through permission-aware execution.

## Dependency graph

```text
                         PROJECTS
                            |
                            v
                    INFRASTRUCTURE API
                            |
          +-----------------+------------------+
          |                 |                  |
          v                 v                  v
       AGENTS          STATE / EVENTS       EXECUTION
          |                 |                  |
          v                 v                  v
       RUNTIME          STORAGE ADAPTERS    TOOL ADAPTERS
          |
          +-----------> MODEL GATEWAY
          |                   |
          |                   v
          |                ROUTER
          |                   |
          |          +--------+--------+
          |          v        v        v
          |       PROVIDER PROVIDER LOCAL
          |
          +-----------> PERMISSION / SANDBOX
```

## Forbidden

```text
Argus → Gemini SDK
Workspace OS → Stripe SDK
Agent → provider-specific session state
Tool → hard-coded runtime implementation
Project → temporary cloud trial
```

These may exist inside adapters, never as the core architectural dependency.

# Runtime Contract

**Status:** FROZEN — architectural contract

## Purpose
Provide a provider-neutral execution environment for an agent.

## Responsibilities
- start and stop agent execution;
- provide the declared execution capabilities;
- enforce runtime isolation policy;
- expose runtime lifecycle;
- support pause/resume/checkpoint integration where supported;
- report runtime failures.

## Non-responsibilities
- model routing;
- task business logic;
- global memory;
- provider selection;
- project policy.

## Inputs
- agent/task configuration;
- execution policy;
- workspace/runtime configuration.

## Outputs
- execution lifecycle;
- runtime observations;
- tool execution environment;
- runtime errors.

## State owned
Runtime-local state required to execute the agent.

## Invariants
1. Runtime replacement must not require project changes.
2. Runtime-local state must not be the only copy of durable task/session state.
3. Runtime capabilities remain subject to permission and sandbox policy.

## Deferred
- exact runtime interface signatures;
- container/VM/process implementation;
- resource limits;
- runtime transport.

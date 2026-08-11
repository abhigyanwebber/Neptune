# Agent Contract

**Status:** FROZEN — architectural contract

## Purpose
Represent a runtime actor that performs task work through model reasoning and permitted capabilities.

## Responsibilities
- execute within a task;
- maintain an agent role;
- interact with the model abstraction;
- request capabilities through tools;
- observe results;
- participate in verification/recovery;
- maintain session identity.

## Non-responsibilities
- provider management;
- global resource management;
- direct unrestricted host execution;
- project-specific business logic;
- owning durable infrastructure state outside its scope.

## Inputs
- task;
- context;
- role;
- runtime;
- policy.

## Outputs
- execution actions;
- tool requests;
- results;
- artifacts;
- lifecycle events.

## State owned
- agent identity;
- role;
- lifecycle state;
- runtime binding;
- current execution metadata.

## Invariants
1. An agent operates within a task context.
2. Model access occurs through the model abstraction.
3. External effects occur through capability/permission boundaries.
4. Agent state remains attributable to a session.

## Deferred
- exact agent class/interface;
- planning implementation;
- delegation protocol.

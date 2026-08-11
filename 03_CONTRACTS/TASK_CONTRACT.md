# Task Contract

**Status:** FROZEN — architectural contract

## Purpose
Represent a durable unit of requested work.

## Responsibilities
- identify the requested work;
- preserve lifecycle state;
- preserve constraints and requirements;
- support parent/child task relationships;
- provide the durable anchor for agent execution;
- associate checkpoints and artifacts with work.

## Non-responsibilities
- choosing a model;
- executing tools;
- enforcing sandbox isolation;
- implementing project business logic;
- directly managing provider credentials.

## Inputs
- request;
- project namespace;
- constraints;
- requirements;
- optional parent task;
- execution policy.

## Outputs
A durable task record and lifecycle transitions.

## State owned
- task identity;
- project identity;
- lifecycle state;
- constraints;
- requirements;
- parent/child relationships;
- completion/cancellation state.

## State consumed
- policy;
- project context;
- execution results.

## Invariants
1. Task identity remains stable across retries/resume.
2. Task state is not owned exclusively by a runtime.
3. Child tasks remain attributable to their parent.
4. Completion requires the task's declared verification boundary.

## Failure/recovery
A task may pause, fail, resume, or be retried without creating a new logical task unless explicitly forked.

## Events
Lifecycle changes are observable as events.

## Deferred
- exact task state machine implementation;
- persistence technology;
- exact dependency representation.

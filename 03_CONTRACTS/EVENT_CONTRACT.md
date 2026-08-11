# Event Contract

**Status:** FROZEN — architectural contract

## Purpose
Record significant execution occurrences for observability, audit, and recovery-oriented history.

## Responsibilities
- record immutable execution events;
- preserve actor/task/session attribution;
- preserve event type and payload;
- support later replay/audit semantics.

## Non-responsibilities
- deciding business outcomes;
- replacing current state storage;
- executing actions.

## Inputs
- event type;
- task/session/agent correlation;
- actor/source;
- timestamp;
- payload.

## Outputs
An append-only event record.

## State owned
Event history.

## Invariants
1. Events are not silently rewritten as execution proceeds.
2. Important state transitions are attributable to events.
3. Event consumers must not assume every event is a command.
4. Event records must support correlation to the execution that produced them.

## Deferred
- exact event taxonomy;
- event ordering guarantees;
- event-store technology;
- replay implementation;
- idempotency mechanism.

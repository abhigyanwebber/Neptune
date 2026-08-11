# Phase 1 Acceptance Gates

## Gate 1 — Contract integrity

- schemas validate;
- repositories satisfy contract behavior;
- provider SDKs are isolated to adapters.

## Gate 2 — Durable state

- create task;
- create session;
- record turn;
- append event;
- checkpoint;
- restart process;
- recover same task/session identity.

## Gate 3 — Model abstraction

- invoke one free model through Model Gateway;
- no core provider import;
- record provider/model metadata;
- normalize errors.

## Gate 4 — Safe execution

- model requests one safe tool;
- permission engine evaluates it;
- sandbox executes it;
- bounded output is returned;
- denial is enforced independently of model output.

## Gate 5 — Failure recovery

Force:
- provider timeout;
- provider rejection;
- runtime termination;
- malformed tool output.

Expected:
- task/session state survives;
- failure is observable;
- retry/fallback path is deterministic.

## Gate 6 — Economic control

- exhaust free provider quota in a test environment;
- verify fallback/queue behavior;
- verify paid escalation requires explicit budget authority;
- verify no hidden provider spend.

## Gate 7 — Context control

- generate large tool output;
- verify output bounding;
- run a long session;
- verify compaction preserves active constraints and task state.

## Gate 8 — Deployment

- build container image;
- start reference stack;
- run health checks;
- connect database;
- perform one complete task.

## Gate 9 — Restore

- destroy runtime;
- restore state/checkpoint;
- resume task;
- verify artifacts/events remain attributable.

## Gate 10 — Replaceability

Remove the first provider adapter and configure a second candidate.

Expected:
- core/application code unchanged;
- only registry/config/adapter changes required.

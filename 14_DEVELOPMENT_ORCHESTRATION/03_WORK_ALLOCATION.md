# Work Allocation Model

The two accounts are parallel implementation lanes, not two independent projects.

## Initial allocation

### Lane A — Core

1. repository/application skeleton;
2. domain models;
3. task/session lifecycle;
4. state/persistence boundary;
5. event system;
6. checkpoint/recovery;
7. core execution control;
8. context integration.

### Lane B — Infrastructure

1. technology evaluation;
2. model gateway;
3. provider adapter;
4. model registry;
5. basic routing;
6. safe tool interface;
7. permission boundary;
8. sandbox;
9. observability;
10. deployment integration.

## First convergence point

The first meaningful integration target is:

```text
create task
 → create session
 → assemble context
 → request model
 → receive response
 → request safe tool
 → authorize
 → execute
 → record event
 → checkpoint
 → resume
 → complete
```

Neither worker is considered complete until its part participates in this vertical slice.

## Rebalancing

The director may change assignments based on:

- dependency bottlenecks;
- account availability;
- implementation difficulty;
- discovered coupling;
- test failures;
- critical-path impact.

## Principle

> Parallelize independent work. Do not parallelize dependencies merely to keep both accounts busy.

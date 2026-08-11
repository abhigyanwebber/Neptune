# Development Definition of Done

A task is Done only when:

1. implementation satisfies the assignment;
2. relevant contract is respected;
3. tests pass;
4. meaningful failure paths are considered;
5. no known critical TODO remains hidden;
6. dependencies are recorded;
7. implementation decisions are recorded when material;
8. development state is updated;
9. work is committed;
10. handoff is possible from repository state alone.

## Integration Done

A feature is Integration Done only when:

- it works with the other worker's relevant interfaces;
- cross-component tests pass;
- no contract regression is known;
- the integration branch is stable.

## Production readiness

Production readiness is a later gate.

Passing unit tests does not equal production readiness.

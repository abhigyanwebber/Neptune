# Git Integration Protocol

## Branches

```text
main
integration
worker/claude-a
worker/claude-b
```

Workers work on their own branches.

## Commit rules

Commits should be:

- coherent;
- task-scoped;
- descriptive;
- free of secrets;
- test-backed where practical.

## Integration

```text
worker branch
 → commit
 → tests
 → PR/integration request
 → review
 → integration branch
 → cross-worker tests
 → main
```

## Conflict rule

A Git conflict is not automatically an architecture conflict.

Resolve ordinary textual conflicts within the implementation.

Escalate when the conflict represents disagreement about:

- contract;
- ownership;
- architecture;
- security;
- durable state;
- dependency direction.

## Main branch

`main` represents the latest accepted Neptune state.

It must not be used as a scratchpad.


## Local workspace isolation

Each worker's Git clone/working tree is independent.

```text
Neptune-A → worker/claude-a
Neptune-B → worker/claude-b
```

A worker must never rely on another worker's uncommitted local files.

Only committed/pushed work is considered shareable development state.

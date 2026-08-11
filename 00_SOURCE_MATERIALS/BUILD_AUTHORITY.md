# Build Authority

**Purpose:** Tell a future implementation agent how to interpret this repository.

## The repository describes a system, not a finished codebase.

The implementation agent must preserve:

1. project-agnostic infrastructure;
2. provider/model replaceability;
3. infrastructure-owned durable execution state;
4. capability/permission/sandbox separation;
5. task → agent → session → turn execution lineage;
6. event attribution;
7. context as a managed resource;
8. Git/checkpoint separation;
9. resource lifecycle and expiring-resource independence;
10. security enforcement outside model instructions.

## The implementation agent may choose

- language;
- frameworks;
- database technology;
- exact internal class/module structure;
- exact algorithms where not frozen;
- deployment technology;
- provider adapters.

## The implementation agent may not silently change

- core ownership boundaries;
- provider independence;
- security boundaries;
- durable-state ownership;
- project isolation;
- the meaning of Task/Agent/Session;
- the fact that tools are capabilities rather than permissions.

## When uncertain

1. Check the relevant contract.
2. Check the architecture boundary.
3. Check the ADRs.
4. Check whether the question is explicitly deferred.
5. If still unresolved, record an implementation decision rather than silently altering architecture.

## What this document does not authorize

It does not authorize implementing every concept in the Bible at once.

Phase 1 should begin with the smallest reference implementation that validates the core execution spine.

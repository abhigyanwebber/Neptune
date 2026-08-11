# Repository Status

**Package:** Neptune Infrastructure Bible v0.7.1  
**Phase:** Architecture complete / final implementation handoff  
**Status:** Ready for reference implementation

## v0.7.1 purpose

v0.7.1 closes the remaining gap between the architecture and implementation by defining a concrete first-build reference stack, component graph, data flow, build order, behavioral interfaces, fallback matrix, and Phase 1 acceptance gates.

## Completed

- Neptune identity and mission;
- production + free/cheap economic objective;
- project-agnostic architecture;
- core domain model;
- state ownership rules;
- security boundaries;
- model/provider abstraction;
- runtime/tool/permission/sandbox separation;
- event and checkpoint semantics;
- resource lifecycle;
- research integration;
- model supply strategy;
- student/free resource portfolio;
- reference production topology;
- provisional reference implementation candidates;
- first vertical slice;
- build dependency order;
- reference interfaces;
- fallback matrix;
- implementation acceptance gates;
- final architecture audit.

## Still variable by design

- exact provider/model names at activation time;
- exact router scoring weights;
- retrieval/ranking algorithm;
- exact sandbox hardening profile;
- exact scale-out topology;
- advanced multi-agent protocol.

These are implementation variables, not missing architectural fundamentals.

## Phase transition

The Bible construction phase is complete.

The next work is implementation, validation, and empirical refinement. Any architectural change discovered during implementation must be recorded through an ADR and must not be smuggled in as a coding convenience.


## v0.7.1 correction

The candidate implementation stack is explicitly **not frozen**.

Claude/the implementation agent retains authority over concrete technology selection, provided the selected implementation satisfies Neptune's frozen architectural contracts, security boundaries, production requirements, and free/cheap economic objective.


## v0.7.1 additions

- two-account development methodology;
- explicit Claude A / Claude B roles;
- account bootstrap protocol;
- contract-first parallelism;
- worker development-state templates;
- Git integration protocol;
- director control protocol;
- development definition of done;
- two-agent methodology ADR.

## v0.7.1 final pass

The Bible is now frozen as an architectural handoff.

Final-pass corrections:
- historical Phase 0 draft explicitly marked superseded;
- duplicate ADR numbering removed;
- reference implementation decisions explicitly marked reversible;
- implementation-choice authority reconciled with the reference stack;
- final audit distinguishes frozen architecture from provisional technologies;
- final freeze/change-control document added.

No further Bible expansion is planned before implementation.


## v0.7.1 correction

Added the explicit workspace-isolation rule:

- Claude A and Claude B use separate local Git working copies.
- Both work against the same canonical GitHub repository.
- Local filesystem workspaces are never shared.
- MCP filesystem access should be scoped to the corresponding worker workspace where possible.
- Added `14_DEVELOPMENT_ORCHESTRATION/08_LOCAL_WORKSPACE_SETUP.md`.

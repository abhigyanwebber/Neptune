# Neptune Development Methodology

**Status:** FROZEN DEVELOPMENT METHODOLOGY  
**Scope:** How Neptune is built; not how Neptune operates at runtime.

## 1. Purpose

Neptune will be built by two concurrently operated Claude implementation accounts under a director layer consisting of the human operator and ChatGPT.

This methodology exists to accelerate implementation without creating a second, unnecessarily complex orchestration system.

It is a development protocol, not a Neptune runtime feature.

## 2. Director layer

The director layer consists of:

- **Human operator:** manages the Claude accounts, MCP connections, credentials, GitHub access, task handoff, environment, and practical execution.
- **ChatGPT:** provides architectural direction, scope control, design review, cross-agent coordination guidance, and final interpretation of the Bible.

The directors decide:

- what should be built next;
- how work is divided;
- whether work belongs inside Neptune;
- whether an implementation decision violates the architecture;
- whether a cross-domain conflict requires intervention;
- when a milestone is accepted.

## 3. Two Claude implementation accounts

There are exactly two implementation lanes in the initial production methodology:

### Claude A — Core / Control Plane

Primary responsibility:

- core domain;
- task/session/turn lifecycle;
- state and persistence boundaries;
- event system;
- checkpoint/recovery;
- core execution/control services;
- context subsystem where it depends on the core;
- internal APIs/contracts.

### Claude B — Infrastructure / Integration

Primary responsibility:

- model gateway;
- provider integrations;
- model registry;
- routing implementation;
- tool integrations;
- permission enforcement implementation;
- sandbox implementation;
- observability integrations;
- deployment/infrastructure adapters;
- external service integrations.

## 4. Important: roles are domains, not permanent ownership of every future feature

The two role descriptions establish a default division of work.

The director layer may rebalance individual tasks when the dependency graph, workload, or implementation discoveries make another assignment more efficient.

A role must not be used as an excuse to modify another domain's architectural boundary without coordination.

## 5. How each account is initialized

The same Neptune Bible/repository is supplied to both Claude accounts.

The implementation prompt should tell the account:

> You are one of Neptune's two implementation agents. Read the Neptune Bible completely before modifying the repository. Your account identity will then be supplied as either **A** or **B**. Once your identity is supplied, load the corresponding role from `14_DEVELOPMENT_ORCHESTRATION/01_WORKER_ROLES.md`, inspect the current development state, and work only on tasks assigned to your role unless the director layer authorizes otherwise.

After the account is told whether it is **A** or **B**, it must:

1. identify itself in the development state;
2. read the role definition;
3. inspect the current roadmap and dependency graph;
4. inspect existing work and recent commits;
5. identify its current assignment;
6. check dependencies and interface freezes;
7. implement only the authorized work;
8. test its work;
9. update development state;
10. commit to its worker branch;
11. report completion/blockers/decisions.

The account must not assume that being A or B gives it authority over the other account.

## 6. Shared repository, isolated work

Both accounts work against the same canonical Neptune GitHub repository.

They should use separate worker branches.

```text
main
 ├── worker/claude-a
 └── worker/claude-b
```

Completed work moves through:

```text
worker branch
 → tests
 → commit
 → pull request
 → review/integration
 → integration branch
 → system validation
 → main
```

Direct uncontrolled modification of `main` is prohibited by the development methodology.

## 6A. Workspace isolation

The two implementation accounts must **never simultaneously operate on the same writable local directory**.

Both accounts work against the same canonical GitHub repository, but each account receives an independent local Git working copy.

Example:

```text
C:\Neptune\
├── Neptune-A\    ← Claude A working copy
└── Neptune-B\    ← Claude B working copy
```

The canonical repository remains the shared source of truth:

```text
GitHub / Neptune
├── main
├── worker/claude-a
└── worker/claude-b
```

The relationship is:

```text
GitHub repository
       │
   ┌───┴────┐
   ↓        ↓
Neptune-A  Neptune-B
   │        │
Claude A  Claude B
```

### Rules

- Claude A operates only from its assigned workspace and branch.
- Claude B operates only from its assigned workspace and branch.
- The two Claude accounts must not share a writable filesystem workspace.
- Neither account should switch into or modify the other account's working copy.
- Cross-agent coordination occurs through GitHub, commits, branches, pull requests/integration, and repository development-state files.
- MCP filesystem access should be scoped to the corresponding worker workspace whenever technically possible.
- Shared read-only reference material may be exposed separately, but the implementation workspaces remain isolated.
- A local path is an operational detail; the Bible does not mandate a specific operating-system path.

This isolation exists to prevent accidental file overwrites, branch confusion, uncommitted-change collisions, and ambiguous authorship while preserving a single canonical repository.

## 7. Contract-first parallelism

When two tasks need to proceed in parallel:

1. shared interfaces/contracts are defined or confirmed first;
2. those interfaces become temporarily frozen;
3. each Claude may implement independently behind the boundary;
4. interface changes require director review.

This is the primary mechanism for obtaining parallel speed without uncontrolled coupling.

## 8. Worker state must live in the repository

No critical development knowledge may exist only inside a Claude conversation.

The repository should maintain machine-readable or clearly structured development state covering at minimum:

- current worker identity;
- current assignment;
- status;
- completed work;
- in-progress work;
- blockers;
- dependencies;
- interface changes;
- decisions;
- tests;
- next action.

A replacement Claude account must be able to recover the work state from the repository.

## 9. Implementation authority

Claude has authority over implementation choices inside its assigned domain, provided they satisfy the frozen Neptune architecture and constraints.

Claude may:

- select concrete libraries;
- replace candidate technologies;
- restructure internal implementation;
- optimize code;
- choose implementation algorithms where the Bible leaves them open.

Claude must escalate:

- architectural changes;
- contract changes;
- security-boundary changes;
- changes to durable-state ownership;
- changes that introduce a new hard dependency;
- changes that materially alter the free/cheap production objective;
- cross-domain changes that affect the other worker.

## 10. Definition of done

A task is not complete merely because code exists.

The assignment is complete when its task-specific acceptance criteria are satisfied and the worker has:

- implemented the required behavior;
- run relevant tests;
- verified contract compliance;
- documented meaningful decisions;
- recorded known limitations;
- updated development state;
- committed the work;
- provided a concise handoff/report.

## 11. Handoff

A worker may hand work to the other worker.

The handoff must identify:

- what was completed;
- what remains;
- changed interfaces;
- dependencies;
- known bugs;
- tests run;
- files/commits;
- exact next action.

The receiving worker must not rely on private conversation history.

## 12. Failure and replacement

If one Claude account becomes unavailable, rate-limited, corrupted, or otherwise unusable:

1. preserve its branch and commits;
2. preserve its development-state record;
3. preserve its handoff;
4. the director assigns the work to the other account or a replacement account;
5. the replacement begins from repository state.

The methodology must never depend on a single Claude account remembering the project.

## 13. Integration authority

Neither worker has unilateral authority to redefine Neptune.

The director layer resolves:

- conflicting architectural interpretations;
- breaking contract proposals;
- cross-domain ownership disputes;
- major technology substitutions;
- scope disputes.

## 14. Scope control

The two-worker arrangement exists to accelerate the defined Neptune build.

It must not be used to increase scope merely because additional parallel capacity exists.

If a worker becomes idle, the default response is not "invent more work."

The director should:

1. accelerate a blocked dependency;
2. improve validation;
3. perform integration;
4. document a discovered issue;
5. or wait.

## 15. End state

The methodology succeeds when two Claude accounts can work in parallel while:

- sharing one architecture;
- sharing one repository;
- preserving isolated work;
- minimizing waiting;
- minimizing conflicts;
- keeping implementation decisions traceable;
- allowing either account to recover the other's work;
- keeping the human/operator workload manageable.

This is intentionally simple.

We are not building an orchestration platform to manage the construction of Neptune.

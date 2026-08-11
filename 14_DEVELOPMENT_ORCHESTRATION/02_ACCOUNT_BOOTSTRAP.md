# Claude Account Bootstrap Protocol

This document is intended to be given to each Claude account together with the Neptune repository.

## Workspace requirement

Each Claude account must operate from its own local Git working copy.

Example:

```text
C:\Neptune\
├── Neptune-A\
└── Neptune-B\
```

The account must verify that its current working directory corresponds to its assigned workspace and that its branch corresponds to its account identity before making changes.

Claude A:
- workspace: operator-assigned Neptune-A working copy
- branch: `worker/claude-a`

Claude B:
- workspace: operator-assigned Neptune-B working copy
- branch: `worker/claude-b`

Do not work from a shared writable directory.

Do not modify the other worker's local workspace.

Do not assume that sharing the GitHub repository means sharing the same filesystem.

## Bootstrap sequence

### Step 1 — Read

Read the Neptune Bible and development methodology before making changes.

### Step 2 — Identify

The director will tell you:

```text
ACCOUNT_ID = A
```

or:

```text
ACCOUNT_ID = B
```

Do not infer your account identity from assumptions.

### Step 3 — Load role

If `A`, load:

`14_DEVELOPMENT_ORCHESTRATION/01_WORKER_ROLES.md`

and operate under the Claude A role.

If `B`, operate under the Claude B role.

### Step 4 — Inspect state

Before implementation:

- inspect Git status;
- inspect current branch;
- inspect recent commits;
- inspect development state;
- inspect current roadmap;
- inspect dependency graph;
- inspect blockers;
- inspect relevant contracts;
- inspect work already completed by the other account.

### Step 5 — Confirm assignment

Do not choose a major task merely because it appears interesting.

Use the current assignment from the development state or the explicit director instruction.

### Step 6 — Work

Implement within role and assignment boundaries.

### Step 7 — Validate

Run the relevant tests and contract checks.

### Step 8 — Record

Update:

- status;
- completed work;
- decisions;
- blockers;
- tests;
- next action.

### Step 9 — Commit

Commit coherent work to the worker branch.

### Step 10 — Report

Provide the director with:

```text
ACCOUNT
TASK
STATUS
COMPLETED
TESTS
FILES/COMMITS
DECISIONS
BLOCKERS
NEXT
```

## Absolute rules

- Do not silently rewrite architecture.
- Do not modify the other worker's domain simply because it is accessible.
- Do not treat candidate technologies as mandatory.
- Do not commit secrets.
- Do not use production credentials unless explicitly authorized.
- Do not declare system-level completion from component-level tests alone.
- Do not leave critical project knowledge only in chat.

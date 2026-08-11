# Development State

This document defines the minimum state that must be maintained in the repository.

## Required records

The live development repository should contain:

```text
DEVELOPMENT_STATE/
├── workers.yaml
├── assignments.yaml
├── dependencies.yaml
├── blockers.yaml
├── decisions.yaml
└── integration_queue.yaml
```

## Worker record

```yaml
worker_id:
account_role:
branch:
status:
current_task:
last_update:
```

## Assignment record

```yaml
task_id:
title:
owner:
status:
depends_on:
blocks:
acceptance:
```

## Blocker record

```yaml
blocker_id:
task:
owner:
description:
dependency:
director_action:
status:
```

## Rule

These files describe the current production state.

They should be concise enough that either Claude can inspect them quickly.

They are not intended to become a second project-management product.

# Backup and Disaster Recovery

## Recovery classes

### R0 — Disposable
Caches, temporary runtime state.

### R1 — Recoverable
Sessions and temporary artifacts.

### R2 — Important
Agent state, task records, memory and event logs.

### R3 — Critical
Infrastructure configuration, provider registry, architecture specifications and secret metadata.

Secret values must not be placed in ordinary backups unless encrypted and explicitly intended.

## Recovery tests

At Phase 0 validation, test:

- restore task from checkpoint;
- restore session after runtime death;
- reconstruct state without provider session;
- replace a provider;
- replace a resource;
- restore architecture registry from backup.

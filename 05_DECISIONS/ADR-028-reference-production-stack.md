# ADR-028 — Reference Production Stack Is Concrete but Replaceable

**Status:** FROZEN  
**Scope:** Phase 0

## Decision

Neptune will maintain a concrete reference stack so implementation can start without rediscovering the research.

The reference stack includes:

- GitHub + GitHub Actions for source/CI;
- LiteLLM as the model gateway;
- free multi-provider inference lanes;
- local support inference;
- a replaceable relational state provider;
- a lightweight persistent compute candidate;
- observability;
- secret management;
- controlled execution and sandboxing;
- burst cloud/GPU resources.

## Why

The research demonstrates that the free/cheap ecosystem is volatile. A useful implementation therefore needs a known-good starting configuration without making those providers architectural dependencies.

## Consequence

The implementation agent should first implement against the reference stack and validate it.

Replacing a resource is expected to be a registry/adapter operation, not a core architecture change.

## Not decided

Exact production provider, deployment region, database, sandbox technology, and model versions remain implementation choices subject to current verification.

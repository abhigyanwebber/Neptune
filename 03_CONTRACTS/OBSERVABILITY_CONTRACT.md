# Observability Contract

**Status:** FROZEN — architectural boundary

## Purpose
Make important infrastructure behavior measurable and attributable.

## Responsibilities
- record relevant events/metrics;
- correlate model/tool/runtime/task activity;
- support failure diagnosis;
- support usage/cost accounting where data is available.

## Non-responsibilities
- becoming task state itself;
- deciding authorization;
- altering execution semantics.

## Invariants
1. Important actions should be attributable to task/session/agent.
2. Observability must not require a single vendor.
3. Sensitive information must respect redaction policy.

## Deferred
- telemetry backend;
- metric naming implementation;
- tracing protocol;
- retention.

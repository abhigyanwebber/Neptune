# Reference Build Order

**Purpose:** prevent parallel complexity from hiding foundational defects.

## Stage 0 — repository and contracts

Deliver:
- project skeleton;
- configuration loading;
- domain objects;
- contract tests;
- schema validation;
- logging baseline.

Gate: contracts and schemas load/validate.

## Stage 1 — durable state

Deliver:
- PostgreSQL connection;
- task repository;
- session repository;
- turn repository;
- event append/read;
- checkpoint repository;
- migrations.

Gate: kill/restart process without losing durable task/session state.

## Stage 2 — model gateway

Deliver:
- normalized request/response types;
- capability requirement model;
- provider adapter interface;
- LiteLLM integration;
- one verified free provider candidate.

Gate: bounded model request succeeds without provider SDK leaking into core.

## Stage 3 — execution loop

Deliver:
- context assembly;
- model turn;
- tool intent parsing;
- one safe tool;
- permission decision;
- sandbox execution;
- event recording.

Gate: one bounded coding task completes end-to-end.

## Stage 4 — recovery

Deliver:
- checkpoint creation;
- resume;
- provider failure handling;
- runtime failure handling.

Gate: forced failure resumes the same logical task.

## Stage 5 — economics and resilience

Deliver:
- second provider;
- quota ledger;
- health/cooldown;
- fallback policy;
- budget envelope;
- usage reports.

Gate: primary free lane can be exhausted without architectural failure or uncontrolled spend.

## Stage 6 — context hardening

Deliver:
- tool-output limits;
- compaction;
- repository map/search strategy;
- context provenance.

Gate: long tool-heavy session remains bounded.

## Stage 7 — operations

Deliver:
- structured telemetry;
- Sentry/OpenTelemetry integration;
- backups;
- deployment automation;
- resource lifecycle checks.

Gate: operator can determine what happened, what failed, and what resources were consumed.

## Stage 8 — optional capabilities

Only after the core passes:
- local support model;
- additional runtimes;
- MCP expansion;
- multi-agent execution;
- advanced routing;
- project-specific integrations.

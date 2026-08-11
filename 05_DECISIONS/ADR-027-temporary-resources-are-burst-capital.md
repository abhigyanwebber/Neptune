# ADR-027 — Temporary Resources Are Burst Capital

**Status:** FROZEN  
**Scope:** Phase 0

## Context

Student programs, cloud credits, trials, and promotional quotas can provide substantial temporary capacity.

## Decision

Temporary resources are treated as burst capital.

They are appropriate for:

- experimentation;
- migrations;
- benchmark runs;
- short GPU workloads;
- capacity spikes;
- temporary staging;
- high-value workloads that can later return to the durable baseline.

They should not silently become mandatory foundations for normal operation.

## Consequence

Every critical temporary dependency requires a replacement or graceful-degradation path before it is promoted into a core workload.

## Not decided here

Exact cloud allocation and workload placement remain implementation/operations decisions.

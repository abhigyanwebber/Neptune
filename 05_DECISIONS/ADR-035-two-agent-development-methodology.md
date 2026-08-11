# ADR-035 — Two-Agent Neptune Development Methodology

**Status:** FROZEN DEVELOPMENT METHODOLOGY  
**Scope:** Neptune construction process

## Decision

Neptune will initially be built by two Claude implementation accounts under a director layer consisting of the human operator and ChatGPT.

Claude A owns the default Core/Control Plane lane.

Claude B owns the default Infrastructure/Integration lane.

Work proceeds through shared contracts, separate Git branches, explicit repository development state, and controlled integration.

## Why

This provides meaningful parallelism while keeping coordination risk substantially lower than a large multi-agent swarm.

## Important boundary

This methodology is not part of Neptune's runtime architecture.

It is a temporary/operational method for constructing Neptune.

## Consequence

The development process can change later without changing Neptune itself.

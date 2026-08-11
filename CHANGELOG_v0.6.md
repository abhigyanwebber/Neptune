# Neptune Infrastructure Bible v0.6 — Final Building Phase

## Purpose
v0.6 closes the remaining gap between the architectural Bible and a first reference implementation.

## What changed
- Promoted Phase 0 from "implementation-ready architecture" to "architecture complete".
- Added a normative reference implementation specification.
- Added a concrete build order with dependency gates.
- Added reference technology choices while preserving adapter-level replaceability.
- Added component graph and end-to-end data-flow specifications.
- Added reference interfaces for the first vertical slice.
- Added a reference stack registry and resource fallback matrix.
- Added Phase 1 acceptance tests and explicit implementation invariants.
- Added a final foreign-agent implementation handoff.
- Added a final architecture consistency audit document.
- Corrected the README/status language so the package no longer mixes Phase 0 deferral with implementation readiness.

## What did not change
- Provider independence.
- Project-agnostic core.
- Infrastructure-owned durable state.
- Permission/sandbox separation.
- Event-first observability.
- $0 baseline requirement.
- Temporary-credit-as-burst-capital rule.
- Model/resource facts remaining outside core architecture.

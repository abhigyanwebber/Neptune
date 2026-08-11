# ADR-033 — One Provider Before Multi-Provider Resilience

## Decision
The first vertical slice uses one currently verified free provider/model candidate. A second provider is added only after the core execution loop passes.

## Rationale
Multiple providers cannot compensate for a broken task/session/runtime foundation. The correct order is correctness first, resilience second.

## Consequence
Early testing is simpler while the architecture still proves replaceability before scale.

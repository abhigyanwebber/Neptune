# ADR-041 — Registry Canonical Source

**Status:** DECISION
**Scope:** Cross-lane (Claude A registry, Claude B model/provider registry) — C-001 Registry Consolidation Analysis

## Decision

Neptune's canonical registry architecture is the **Postgres-backed registry system** in `src/core/registry/*` (Capability, Provider, Resource, Tool-definition catalogs — A-003/A-004, consumed by the Resolution layer — A-006). The YAML-file-based, in-memory `ModelRegistry` in `src/neptune/infrastructure/models/registry.py` (B-001) is superseded and scheduled for migration into the canonical system. Full inventory, compatibility matrix, and migration plan: `DIRECTOR_DECISION_REGISTRY.md`.

This ADR does not itself perform the migration. It establishes which system future work should converge on.

## Rationale

Two registry systems exist today because they were built sequentially by independent lanes, not chosen between: B-001 built `ModelRegistry` before A-003 (the Postgres registry) existed at all, so B never had a canonical system to integrate with. Consolidation is possible now, and low-risk, because **no system currently depends on both** — the two registries have never been asked to agree with each other, so choosing one does not break a live cross-dependency.

The Postgres system is the stronger long-term foundation on the criteria that matter most for Neptune's stated architecture (persistence-first, resumable, auditable — `01_BIBLE/01_VISION_AND_PRINCIPLES.md`):
- **Verification support:** structured `verification_source`/`verification_status`/`last_checked` fields plus a full audit trail via the existing Event infrastructure (every mutation is queryable history), versus a single timestamp field with no system-level change history beyond git.
- **Reproducibility:** both are git-versioned, but only the Postgres system's reload/recovery behavior has genuine two-OS-process integration test evidence (A-004, A-006).
- **Future scalability:** the Postgres system already has four entity types (Capability/Provider/Resource/Tool) and a generic, reusable cross-type dependency resolver (`core.registry.dependency_resolution`, A-003) — exactly the "providers, tools, sandboxes, MCP servers and cloud resources become interchangeable" charter A-003 was scoped against. `ModelRegistry` covers only Model/Provider, with no dependency concept and no path to the other entity types without rebuilding what A-003 already built.

The one criterion that currently favors the YAML system — **runtime compatibility** — is honestly acknowledged as a real, nontrivial cost of this decision, not dismissed. `ModelRegistry` is, today, the only registry in the codebase with a real, live-tested runtime consumer (B-003's live Groq validation runs through it via `GatewayService` → `CapabilityRouter`). Choosing the Postgres system as canonical does not change that fact today; it names the target state and the follow-up work required to make it true, per `DIRECTOR_DECISION_REGISTRY.md` §4.

Migration effort is real but bounded and scoped, not open-ended: the Postgres `Provider` schema needs a new Model entity (mirroring the same pattern A-003 already used for its other four entity types) and several additive operational fields B's `ProviderRecord` has and A's lacks (regions, endpoints, pricing_snapshot, quota_snapshot, health, terms_url, failure_history, fallback_providers, cache_characteristics). The capability vocabulary needs reconciling (five values differ on each side) — recommended as a non-destructive union extension, following the same precedent already set when `ollama`/`openai_compatible` were added to `KNOWN_PROVIDERS` (ADR-A-011). None of this requires dismantling completed work; all of it is additive.

## Consequences

- `ModelRegistry`, `config/registries/model_registry.yaml`, and `config/registries/provider_registry.yaml` are deprecated as of this decision and should not gain new capability without a documented reason to delay the migration further.
- New follow-up tasks are required before this decision is operationally true rather than just architecturally decided: a Model entity on the Postgres side, schema field extension, capability vocabulary reconciliation, a `ModelGatewayPort` adapter reading from the Resolution layer, and finally cutting `GatewayService` over. None of these are performed by this ADR.
- Until the follow-up work lands, `ModelRegistry` remains the actual operational source for the one live execution path that exists. This ADR does not require that path to be broken or paused while migration work proceeds — the deprecated system keeps functioning until its replacement is verified working, then a single cutover happens (not a partial one), per the migration plan's sequencing recommendation.
- This decision does not address the duplicate ADR-039/ADR-040 numbering or the stale `00_ADR_INDEX.md` identified in `DIRECTOR_REVIEW_001.md` — those remain open, separate corrections.

## Validation

Revisit if the follow-up work (`DIRECTOR_DECISION_REGISTRY.md` §4) surfaces a reason the Model entity genuinely cannot be represented well in the existing Postgres schema — e.g. if per-model operational data (quota, health) turns out to need update frequency or query patterns fundamentally mismatched with the existing one-commit-per-call repository pattern (ADR-A-002). No such evidence exists today; this is a reason to watch during migration, not a reason to delay this decision.

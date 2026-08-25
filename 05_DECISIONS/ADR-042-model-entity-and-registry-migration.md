# ADR-042 — Canonical Model Entity, Provider Field Migration, and Capability Reconciliation

**Status:** DECISION
**Scope:** Claude A / Canonical Registry Migration (C-004, implementing ADR-041)

## Decision

1. **A new `Model` entity** is added to the canonical registry (`core/registry/model_registry.py`), distinct from `Provider`, representing exactly the five concepts C-004's brief named: model identifier, provider relationship, verification metadata, operational status, and provider-facing model name -- plus `capabilities` (see rationale below) and `depends_on` (for consistency with the other four registries' dependency-resolution support).
2. **`Provider` is extended** with seven fields migrated from the deprecated B-side `ProviderRecord`: `regions`, `endpoints`, `pricing_snapshot`, `quota_snapshot`, `health_snapshot`, `terms_url`, `fallback_providers`. Two B-side fields are deliberately **not** migrated: `failure_history` and `cache_characteristics`.
3. **`KNOWN_CAPABILITIES` is extended** with three values from the deprecated B-side `Capability` enum: `summarization`, `classification`, `embedding`. Two B-side values are deliberately **not** added: `fast_general` and `frontier_escalation`.

## Rationale

### Model entity: why `capabilities` was added despite not being in the named list

C-004's brief lists five concepts to represent, not six -- `capabilities` is absent. But capability reconciliation (item 3 of the same brief) has no purpose unless *something* on the Model side actually carries capability values to reconcile against; C-001's own finding was that model/provider granularity differ (a provider can host multiple models with different capabilities each), so a capability list at the Provider level alone cannot represent per-model variation. Omitting `capabilities` from `Model` would mean this migration adds the vocabulary reconciliation infrastructure with nothing on the canonical side positioned to use it correctly. This is judged to fall within "how these concepts should be represented" (the brief's own framing for item 1) rather than "inventing a field for theoretical future use" -- it is required for the fields that *are* named to mean anything for a multi-model provider.

### Model entity: why no fixed vocabulary (`strict` mode)

Capability/Provider/Resource/Tool (A-003) each validate their primary id against a small, Neptune-defined, enumerable set. Model ids are provider-published and open-ended -- there is no equivalent small set to define. `ModelRegistry.register()` therefore has no `strict` parameter at all, unlike the other four registries. This is a genuine, deliberate asymmetry, not an oversight.

### Model entity: why `model_id` and `provider_model_name` are separate fields

B-003's live Groq validation found a real bug from conflating the registry's own key with the string actually sent to the provider API (the registry key was rejected by Groq with a 404). Keeping these structurally distinct in the canonical schema, rather than relying on callers to remember the difference, directly closes a failure mode that already happened once.

### Provider field migration: inclusion criteria

`regions`, `endpoints`, `pricing_snapshot`, `quota_snapshot`, `health_snapshot`, `terms_url`, and `fallback_providers` were kept because each represents a fact a future Model Gateway adapter or Router would need to *read* to make a decision (which endpoint to call, whether a provider is in-budget, what to try next on failure) -- i.e. each has a consumer-shaped purpose, not just descriptive value. `health` was renamed to `health_snapshot` to make explicit that it is a point-in-time note (as B's own field was, defaulting to `"unknown"` and never live-updated), not a live telemetry signal -- avoiding the misleading implication that the registry itself monitors health.

`fallback_providers` is kept as a field **distinct from `depends_on`**, not folded into it: `depends_on` (A-003) is a topological "must exist before this works" relationship, consumed by `resolve_dependencies()`. A fallback is a "may substitute if this fails" relationship -- a fundamentally different semantic that should not be resolved as a prerequisite chain. Conflating the two would produce incorrect dependency-resolution results (e.g. treating a fallback provider as something that must be provisioned before the primary provider can be used, which is false).

### Provider field migration: exclusion criteria

`failure_history` (free-text log of past failures) is **not** migrated because Neptune's registry already has a superior mechanism for exactly this purpose: every mutation to a Provider record already emits a `registry.provider.updated` event through the existing audit trail (A-004, `core/registry/audit.py`), which is structured, timestamped, and queryable -- a redundant free-text field would duplicate this with a weaker, unstructured version of the same information, directly contradicting the brief's "avoid duplicate semantic concepts under different names" instruction (which this ADR applies to field-level duplication, not only capability-vocabulary duplication).

`cache_characteristics` (free-text description of prompt-caching behavior) is **not** migrated as a dedicated column because no code anywhere in the repository consumes it structurally (no filter, sort, or decision reads it) -- it is descriptive-only. It fits the existing free-text `notes` field without needing a dedicated column, consistent with "do not invent fields merely for theoretical future use."

### Capability reconciliation: inclusion criteria

`summarization`, `classification`, and `embedding` are added because each names a genuinely distinct task-type capability -- something a model can *do* -- not already expressible by any of the existing ten values, and not reducible to `reasoning` or `coding` without losing meaning. `embedding` in particular has a clear future consumer: `03_CONTRACTS/MEMORY_CONTRACT.md` already exists as a frozen contract this capability would eventually serve.

### Capability reconciliation: exclusion criteria

`fast_general` is **rejected** as a capability because it describes a *latency/performance tier* for general-purpose use, not a task type -- it answers "how fast/cheap" rather than "what can it do," which is what `CostClass` (`free`/`cheap`/`paid`/`frontier`, already present on B's side) already exists to answer. Adding it to the capability vocabulary would create two vocabularies partially encoding the same cost/tier concept under different names -- precisely what the brief's "avoid duplicate semantic concepts under different names" warns against.

`frontier_escalation` is **rejected** as a capability because it describes a *routing/escalation policy* -- "when should this get bumped to a stronger model" -- not a fact about what a specific model can do. This concept already has a home in the frozen Bible ADR set (`05_DECISIONS/00_ADR_INDEX.md`: "ADR-006 — Explicit escalation"), which is a routing-layer decision, not a registry-catalog fact. Registering it as a capability would misplace a policy concept inside a facts catalog.

`neptune.core.domain.capability.Capability` (the B-side enum itself) is **not modified** by this reconciliation -- explicitly out of scope for C-004 (which forbids modifying `RuntimeDriver`/`AgentRuntime`/planning/`ToolExecutor`/`ObservationLoop`, and by extension the B-side code this reconciliation is *about*, not *touching*). The canonical vocabulary (`core.registry.capability_registry.KNOWN_CAPABILITIES`) is what changed; `neptune.core.domain.capability.Capability` remains B's own code until the `GatewayService` cutover milestone C-001 already named as future work.

## Consequences

- A future `GatewayService` cutover (explicitly out of scope here) will need to translate between `neptune.core.domain.capability.Capability` and the now-13-value `KNOWN_CAPABILITIES`, including deciding what a model tagged `fast_general` or `frontier_escalation` in the old YAML data should become in the canonical schema (most likely: `fast_general` maps to a `cost_class` value, dropped as a capability tag; `frontier_escalation` becomes routing metadata, not a capability tag). This ADR does not perform that translation -- it only establishes that the two concepts do not belong in the capability vocabulary, leaving the actual data mapping to whoever performs the cutover.
- `Provider.fallback_providers` and `Provider.depends_on` now coexist with different semantics on the same entity. Any future code consuming `Provider` must not conflate them; this ADR's rationale section exists specifically so that distinction isn't lost.
- The one existing `Provider` record with meaningful operational data on the B side (`groq`) is a natural first candidate to populate the new fields with real data, but doing so is left to the seed-data update accompanying this task rather than treated as a required schema-only change.

## Validation

Revisit the capability-rejection decisions (`fast_general`, `frontier_escalation`) if a future Router design finds it genuinely needs them expressed as capabilities rather than as `CostClass`/escalation-policy concepts -- e.g. if capability-based routing and cost-tier-based routing turn out to need to be expressed in the exact same filtering mechanism. No such evidence exists today.

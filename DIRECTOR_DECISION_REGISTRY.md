# DIRECTOR_DECISION_REGISTRY

**Task:** C-001 — Registry Consolidation Analysis
**Owner:** Claude A
**Nature:** Analysis only. No registry code, runtime code, resolution code, planning code, provider code, tool code, or database migrations were written to produce this document.

---

## 1. Registry Inventory

| Registry | Location | Purpose | Storage | Consumers | Status |
|---|---|---|---|---|---|
| **Capability Registry (A)** | `src/core/registry/capability_registry.py` | Catalog of the fixed capability vocabulary (reasoning, coding, web_search, vision, tool_use, mcp, browser, terminal, memory, planning) | Postgres, via `SqlAlchemyCapabilityRepository` (`CapabilityModel`) | `registry_loader.py`, `CapabilityResolver` (A-006), its own tests. **No runtime consumer.** | Live schema, populated (10 entries via `06_REGISTRIES/data/capabilities.yaml`), zero drift since A-004. |
| **Provider Registry (A)** | `src/core/registry/provider_registry.py` | Catalog of providers (groq, openrouter, gemini, openai, cerebras, mistral, ollama, openai_compatible), status, capabilities, dependencies | Postgres (`ProviderModel`) | `registry_loader.py`, `ProviderResolver` (A-006), its own tests. **No runtime consumer.** | Live schema, 5 of 8 known ids populated with verified data (A-004). No separate per-model granularity. |
| **Resource Registry (A)** | `src/core/registry/resource_registry.py` | Catalog of infrastructure resources (github, postgres, supabase, cloudflare, local_fs, docker), lifecycle status, criticality | Postgres (`ResourceModel`) | `registry_loader.py`, `ResourceResolver` (A-006), its own tests. **No runtime consumer.** | Live schema, all 6 known ids populated. **No equivalent exists anywhere in Claude B's tree.** |
| **Tool Registry (A)** | `src/core/registry/tool_registry.py` | Catalog of tool *definitions* as vocabulary entries (browser, terminal, filesystem, search, mcp) with capability mapping and resource dependencies | Postgres (`ToolDefinitionModel`) | `registry_loader.py`, `CapabilityResolver`/`ResourceResolver` (A-006), its own tests. **No runtime consumer.** | Live schema, all 5 known ids populated. Distinct from B's `ToolRegistry` (see below) — this is a *catalog entry*, not an executable tool binding. **No equivalent catalog concept exists in Claude B's tree.** |
| **Model/Provider Registry (B)** | `src/neptune/infrastructure/models/registry.py` (`ModelRegistry`, `ModelRecord`, `ProviderRecord`) | Loads and validates model + provider facts for the Router; supplies `RoutingCandidate` objects | In-memory, loaded from `config/registries/model_registry.yaml` + `provider_registry.yaml` at construction time. **No database, no persistence of its own.** | `GatewayService` (`neptune/application/gateway_service.py`), which feeds `CapabilityRouter.select()`. **This is the one registry in the entire repository with a real, live-tested runtime consumer** (B-003's live Groq validation ran through this path). | Live, actively used. Exactly one model entry (`groq-llama-3.3-70b-versatile`) and one provider entry (`groq`) currently populated. |
| **Tool Executor's tool registry (B)** | `src/neptune/core/contracts/tool_execution.py` + `src/neptune/infrastructure/tools/*` | *Executable* tool bindings (currently just `EchoTool`) — a different concept from A's Tool Registry (catalog vocabulary vs. runnable implementation) | In-memory, code-level (tool classes registered directly, no YAML) | `ToolExecutor` (B-004), `ToolPortAdapter` (bridges into `core.contracts.tools.ToolPort`, B-006) | Live, real runtime consumer through Claude A's `AgentRuntime` (B-006's genuine recovery proof). **Not in scope for this consolidation** — it is an execution binding, not a fact catalog, and has no counterpart to consolidate against on Claude A's side. |
| **Capability vocabulary (B)** | `src/neptune/core/domain/capability.py` (`Capability` enum) | Code-level enum used by `ModelRecord`/`ProviderRecord`/`RoutingCandidate`/`CapabilityRouter` | Python source (not a registered, queryable catalog — no metadata, no audit trail, no persistence) | `ModelRegistry`, `CapabilityRouter`, `GatewayService` | Live, actively used, but **not a registry in the same sense as A's** — it's a closed enum with no CRUD, no verification metadata, no audit trail. |
| **Integration registry doc** | `06_REGISTRIES/integration_registry.yaml` | Appears to be documentation/tracking of cross-branch integration points (per B-DEC-017 era work), not a runtime registry | Static YAML, not loaded by any Python code found | None found | Documentation artifact, not a functional registry. Out of scope for consolidation but noted for completeness since it was in the audit path. |

**Verification metadata comparison:**

| | Claude A (Postgres) | Claude B (YAML) |
|---|---|---|
| Fields | `verification_date`, `verification_source`, `verification_status`, `last_checked` (A-004) | `verified_at` (models), `verification_date` (providers) — single timestamp, no source/status distinction |
| History | Full audit trail — every register/update/delete emits an `Event` via the existing Event infrastructure (`core/registry/audit.py`), queryable through `EventRepository.list_for_task(SYSTEM_REGISTRY_TASK_ID)` | None — a YAML edit silently overwrites; history exists only via `git log`/`git blame` on the file, external to the running system |
| Enforcement | `strict=True` by default rejects unregistered vocabulary at write time (`UnknownProviderError` etc.) | `pydantic.BaseModel` validates field *shape* (types, required-ness) but not vocabulary membership beyond the `Capability`/`CostClass`/`Availability` enums |

---

## 2. Compatibility Matrix

### 2.1 Dependency graph today

```
Claude A's registries (Postgres)
  <- registry_loader.py, registry_exporter.py (A-004)
  <- CapabilityResolver, ProviderResolver, ResourceResolver (A-006)
  <- (nothing else -- Resolution layer has no consumer yet either)

Claude B's ModelRegistry (YAML, in-memory)
  <- GatewayService
  <- CapabilityRouter (via RoutingCandidate objects GatewayService supplies)
  <- the one live, working execution path (B-003's real Groq call)
```

**No system currently depends on both.** This is the central fact this analysis rests on: consolidation is not yet blocked by any live cross-dependency, because none exists. The two registries have simply never been asked to agree with each other.

### 2.2 Where schemas differ

Claude A's `Provider` (flat, one record per provider) has no equivalent of B's per-*model* granularity. B's `ModelRecord` carries several fields A's `Provider` does not: `context_limit`, `tool_calling`, `structured_output`, `quota` (free text), `health`, `fallbacks`, `preferred_roles`. B's `ProviderRecord` also carries fields A's `Provider` lacks: `regions`, `endpoints`, `pricing_snapshot`, `quota_snapshot`, `health`, `terms_url`, `failure_history`, `fallback_providers`, `cache_characteristics`. Conversely, A's `Provider`/`Resource`/`ToolDefinition` carry a `depends_on` dependency-graph field with a working cross-registry resolver (`resolve_dependencies()`, A-003) that B's schema has no equivalent of at all.

**Structurally, these are not the same entity.** A's registry models *providers* (one record = one provider). B's registry models *models hosted by providers* (one record = one specific model, with a separate, thinner provider record alongside it). Neptune does not currently have a registry that cleanly represents both levels in one place.

### 2.3 Where vocabularies differ

Capability vocabulary overlap is partial:

- **In both:** `coding`, `reasoning`, `planning`, `tool_use`, `vision`
- **Only in A** (`core.registry.capability_registry.KNOWN_CAPABILITIES`): `web_search`, `mcp`, `browser`, `terminal`, `memory`
- **Only in B** (`neptune.core.domain.capability.Capability`): `fast_general`, `summarization`, `classification`, `embedding`, `frontier_escalation`

Provider vocabulary overlap: A's `KNOWN_PROVIDERS` (groq, openrouter, gemini, openai, cerebras, mistral, ollama, openai_compatible) is a superset in breadth (8 ids) of what B's registry currently has data for (1 id: groq) — but B's schema has no equivalent *enforced* vocabulary at all (any `provider` string is accepted by `ModelRecord`/`ProviderRecord`; nothing stops a typo).

### 2.4 Where future integration would fail

1. **Capability translation.** If a future component reads a capability from one system and checks it against the other's vocabulary (e.g. a `PlanStep.capability_id` of `"browser"` checked against B's Router), it would silently fail to match — `"browser"` isn't in B's `Capability` enum at all, so it wouldn't even parse as a valid `pydantic` field. This is a **hard failure mode**, not a soft mismatch — B's schema uses a closed enum, so an out-of-vocabulary capability raises a validation error rather than degrading gracefully.
2. **Model-vs-provider granularity mismatch.** Any future code that expects "one provider = one set of capabilities" (as A's `Provider.capabilities` implies) would get a wrong or over-broad answer for a provider hosting multiple models with different capabilities each (B's actual data model). This doesn't fail today only because A's registry has never been asked to represent more than one model per provider.
3. **Dependency resolution over B's data.** Nothing in B's schema is compatible with `core.registry.dependency_resolution.resolve_dependencies()` — there is no `depends_on` field on `ModelRecord`/`ProviderRecord`. A future attempt to run A's dependency resolver over B's provider data would simply find nothing to resolve (empty map), silently, rather than erroring — a **silent gap**, not a loud one.

---

## 3. Canonical Recommendation

**Option A: Keep the Postgres-backed registry (Claude A's `core/registry/*`) as Neptune's official source of truth for Capability, Provider, Resource, and Tool-definition catalogs.**

### Justification by criterion

- **Existing integrations.** This criterion currently favors Option B in practice (it has the one live runtime consumer), but that reflects *which adapter got built*, not an inherent property of YAML storage. The Resolution layer (A-006) was purpose-built as the consumption point for a future Router (`DIRECTOR_REVIEW_001.md`, §4 "Resolution Layer" already flags this as the intended, un-executed integration). Choosing Option B to match today's wiring would mean keeping the *less capable* system as canonical purely because it was integrated first, and would abandon four completed, tested tasks (A-003, A-004, A-006, plus this analysis) worth of dependency-resolution, audit-trail, and durability infrastructure that has no YAML-side equivalent.
- **Verification support.** Option A is materially stronger: structured `verification_source`/`verification_status`/`last_checked` fields (vs. B's single `verified_at`/`verification_date` timestamp), plus a genuine audit trail via the existing Event infrastructure — every mutation is queryable history, not just a git diff. Option B's verification data is real and was genuinely checked (B-003's live Groq validation even fixed a real bug in it — the `model_id` vs registry-key mismatch), but it has no system-level memory of *when or why* a value last changed beyond the file's git history.
- **Reproducibility.** Roughly even in principle (both are git-versioned data that can be reloaded), but Option A's reproducibility is the more rigorously *proven* of the two — A-004 and A-006 each have genuine two-OS-process integration tests demonstrating that loading the seed data and performing a lookup/resolution produces an identical, durable result after a process restart. No equivalent test exists for B's YAML loading path (reasonably so — it's simpler and needs less proving — but the asymmetry in test evidence is real).
- **Runtime compatibility.** This is Option A's genuine weak point today: nothing in the live execution path reads from it. This is a real cost of choosing Option A, not a reason to avoid choosing it — it is precisely the migration work item this document's §4 exists to name honestly rather than hide.
- **Future scalability.** Strongly favors Option A. Neptune's registry charter (A-003's own task brief: "providers, tools, sandboxes, MCP servers and cloud resources become interchangeable... requires a unified registry") is fundamentally a many-entity-type, many-dependency problem. Option A already has four entity types (Capability/Provider/Resource/Tool) and a generic cross-type dependency resolver; Option B has exactly one entity type pairing (Model/Provider) with no dependency concept and no path to representing Resources or Tool-definitions-as-catalog without inventing new YAML schemas and a new in-memory loader from scratch — essentially reconstructing what A-003 already built.
- **Migration effort.** Genuinely nontrivial in one specific respect, and this document does not minimize it: **Claude A's `Provider` schema currently has no per-model entity.** Migrating B's richer, per-model data (context_limit, tool_calling, structured_output, quota, health, fallbacks, preferred_roles, regions, endpoints, pricing_snapshot, etc.) requires *adding a new Model entity and schema fields to Claude A's registry* — this is real, scoped follow-up work (§4), not a data copy. Weighed against the alternative (dismantling A-003/A-004/A-006's tested dependency-resolution/audit/CRUD machinery to replace it with an enhanced YAML loader), extending Option A's schema is the smaller total effort.

### Why not Option B

The case for Option B rests entirely on "it's the one that currently works." That is a real, legitimate point — architecture that isn't wired to anything real is architecture that hasn't been proven — but it conflates *integration sequencing* with *architectural merit*. B's `ModelRegistry` was built (B-001) before A's registry existed at all; it was never a considered choice between two systems, it was the only registry available at the time. Nothing about YAML-in-memory storage is inherently better suited to Neptune's stated goal of *durable, resumable, audited* state (`01_VISION_AND_PRINCIPLES.md`) than the Postgres system already built to satisfy exactly that goal for every other kind of Neptune state (Task, Session, Turn, Event, Checkpoint, Plan). Choosing Option B would mean registries are the one category of Neptune state that is *not* persistence-first and *not* resumable in the same sense as everything else — a genuine, avoidable inconsistency with the rest of the architecture this audit's own predecessor document (`DIRECTOR_REVIEW_001.md`) found intact everywhere else.

---

## 4. Migration Plan

This is a plan for future work, **not performed as part of this analysis** (database migrations and new registry code are explicitly out of scope for C-001).

### Files to remove (after migration is complete and verified — not now)
- `src/neptune/infrastructure/models/registry.py` (`ModelRegistry`, `ModelRecord`, `ProviderRecord`)
- `config/registries/model_registry.yaml`
- `config/registries/provider_registry.yaml`

### Files to migrate (data, not code)
- The one existing model entry in `config/registries/model_registry.yaml` (`groq-llama-3.3-70b-versatile`) → a new entry in a to-be-created `06_REGISTRIES/data/models.yaml`, once the Model entity below exists.
- The one existing provider entry in `config/registries/provider_registry.yaml` → merge into the existing `groq` entry in `06_REGISTRIES/data/providers.yaml` (already present from A-004; needs field extension, see below, not a new entry).

### Files to deprecate (mark superseded, keep functional during transition)
- `src/neptune/application/gateway_service.py` — keep functioning against `ModelRegistry` until the replacement read path (Resolution layer) is verified working end-to-end, then cut over in one change, not a partial one.
- `src/neptune/infrastructure/routing/capability_router.py` — no change needed to its own logic (it already takes injected `candidates`, decoupled from the registry it currently gets them from); only its caller needs to change.

### Required follow-up tasks (named, not performed here)
1. **Add a Model entity to Claude A's registry.** New `core/registry/model_registry.py` (dataclass + service, following the existing per-file pattern), new `ModelModel` ORM table, new `SqlAlchemyModelRepository`, tests — the same shape of work as A-003 but for one new entity type. This is the largest single piece of follow-up work and should be its own task.
2. **Extend `Provider` schema** with the operational fields B's `ProviderRecord` has and A's lacks: `regions`, `endpoints`, `pricing_snapshot`, `quota_snapshot`, `health`, `terms_url`, `failure_history`, `fallback_providers`, `cache_characteristics`. Additive, backward-compatible (matching the precedent already set by A-004's verification-metadata fields).
3. **Reconcile the capability vocabulary.** Recommend extending `core.registry.capability_registry.KNOWN_CAPABILITIES` to the union of both vocabularies (adding `fast_general`, `summarization`, `classification`, `embedding`, `frontier_escalation`), non-destructively — the same pattern already used for `KNOWN_PROVIDERS` when `ollama`/`openai_compatible` were added (ADR-A-011). Then update `neptune.core.domain.capability.Capability` to be sourced from (or validated against) the same list, closing the divergence identified in §2.3 at the root rather than patching around it.
4. **Build a `ModelGatewayPort` adapter** (already recommended as the top-priority milestone in `DIRECTOR_REVIEW_001.md`, §6) that reads candidates from the (now-extended) Resolution layer instead of `ModelRegistry`. This is the change that actually makes Option A the live source of truth, not just the "official" one on paper — until this lands, the recommendation in §3 is a target state, not a completed migration.
5. **Cut `GatewayService` over** to the new read path in one change, remove the deprecated files listed above, and delete `config/registries/*.yaml`.
6. **Add a provider-independence contract test for `src/neptune/core`**, mirroring `tests/contract/test_core_provider_independence.py` — flagged in `DIRECTOR_REVIEW_001.md` risk #7, worth doing alongside this consolidation since both touch the same trust boundary.

### Sequencing recommendation
Items 1–3 can proceed independently and in parallel with `DIRECTOR_REVIEW_001.md`'s recommended Model Gateway bridge milestone. Item 4 depends on 1–3 being complete. Item 5 depends on 4 being verified working. Item 6 is independent and can happen any time.

---

## 5. Answer to the Success Condition

**What is Neptune's official registry architecture?**

The Postgres-backed registry system in `src/core/registry/*` (Capability, Provider, Resource, Tool-definition catalogs, built in A-003/A-004, consumed by the Resolution layer in A-006) is Neptune's canonical source of truth for provider, resource, tool, and capability facts. The YAML-backed `ModelRegistry` in `src/neptune/infrastructure/models/registry.py` is superseded and scheduled for migration per §4, pending the follow-up tasks named there. Until those follow-up tasks land, `ModelRegistry` remains the *de facto* operational source (it is what the live system actually reads), and this document's recommendation should be understood as the target architecture, not the current one.

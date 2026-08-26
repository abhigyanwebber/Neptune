# DIRECTOR_LEGACY_REGISTRY_AUDIT

**Task:** C-005 — Legacy Registry Consumer & Cutover Audit
**Owner:** Claude B
**Depends on:** C-001, C-002, C-003 (all complete as of this audit)
**Nature of this document:** Audit and preparation only. The final
registry cutover, `ModelGateway` build, `RuntimeDriver`/`AgentRuntime`
modification, and canonical Postgres registry implementation changes
are explicitly out of scope and were not performed.

---

## 1. Complete Legacy Registry Inventory

Located via a targeted scan of `src/`, `tests/`, `scripts/`, and
`config/` for `ModelRegistry`, `ModelRecord`, `ProviderRecord`,
`model_registry.yaml`, `provider_registry.yaml`, and
`config/registries` references (34 hits, 11 files — full-text search
of the whole repository was also run but excluded here as noise: it
mostly matches this document's own predecessors, `DIRECTOR_DECISION_
REGISTRY.md` and the Bible's own conceptual-interface listing in
`01_BIBLE/09_REUSABILITY_AND_EXTENSION.md`, neither of which is code).

| # | File | Classification | What it does |
|---|---|---|---|
| 1 | `src/neptune/infrastructure/models/registry.py` | **PRODUCTION DEPENDENCY** | The legacy registry itself: `ModelRegistry`, `ModelRecord`, `ProviderRecord`. Loads `config/registries/*.yaml` at construction, exposes `candidates_for()`. |
| 2 | `src/neptune/application/gateway_service.py` | **PRODUCTION DEPENDENCY** | `ModelGatewayService.__init__` takes `registry: ModelRegistry`; `infer()` calls `self._registry.candidates_for(...)` as its first line. **This is the live path's sole dependency point — see §2.** |
| 3 | `config/registries/model_registry.yaml` | **PRODUCTION DEPENDENCY / MIGRATION TARGET** | The actual legacy data: one entry (`groq-llama-3.3-70b-versatile`). |
| 4 | `config/registries/provider_registry.yaml` | **PRODUCTION DEPENDENCY / MIGRATION TARGET** | The actual legacy data: one entry (`groq`). |
| 5 | `scripts/run_live_groq_smoke_test.py` | **PRODUCTION DEPENDENCY** | The Runtime stand-in script that proved B-003's live Groq call. Directly instantiates `ModelRegistry.load()`. Not part of the persisted system, but it is the only script that exercises the live path outside of pytest, and it will break silently (not loudly) if the registry is deleted without updating it. |
| 6 | `scripts/probe_groq_models.py` | **MIGRATION TARGET** | Operational helper that tells a human to hand-update `config/registries/model_registry.yaml` after probing live Groq model data. Does not import `ModelRegistry` directly, but is entirely coupled to the legacy data file's existence and format. |
| 7 | `tests/conftest.py` | **TEST DEPENDENCY** | Shared `model_registry` pytest fixture (`ModelRegistry.load(CONFIG_DIR)`), consumed by test files 8 and 10 below. |
| 8 | `tests/test_registry.py` | **TEST DEPENDENCY / MIGRATION TARGET** | The legacy registry's own test suite (schema loading, `ModelRecord` required fields, `candidates_for()`, Router selection against real registry data). This entire file's *purpose* disappears once the registry is deleted — it is not migratable so much as replaceable by an equivalent suite against the canonical registry. |
| 9 | `tests/test_groq_live_e2e.py` | **TEST DEPENDENCY** | Live e2e test using the `model_registry` fixture to run a real Groq call through the full Gateway path. Needs to keep working (or have a canonical-registry equivalent) through and after cutover, since it is the one test that has ever actually proven the live path end-to-end. |
| 10 | `tests/test_gateway_boundary.py` | **DOCUMENTATION** (comment only) | Docstring/comment explains the file's `_StubRegistry` test double exists specifically *so this test doesn't depend on* `config/registries/*.yaml`. No actual `ModelRegistry` import. Zero migration impact. |
| 11 | `tests/test_observation_loop_integration.py` | **DOCUMENTATION** (comment only) | Same pattern as #10 — comment only, uses its own `_StubRegistry`, no real dependency. |
| 12 | `tests/test_tool_execution_integration.py` | **DOCUMENTATION** (comment only) | Same pattern as #10/#11. |

**Not found anywhere in the repository (confirmed by the same scan):**
`tests/test_groq_adapter_mocked.py` and `tests/test_contracts.py` do
**not** depend on `ModelRegistry` in any way (`GroqAdapter` is
constructed directly with a fixed `GroqConfig` in the mocked tests;
`test_contracts.py`'s provider-independence check is orthogonal). No
dead/unused legacy-registry code was found — every production
reference is load-bearing for the one live path that exists (B-003's
Groq validation), which matches `DIRECTOR_DECISION_REGISTRY.md` §1's
own finding that this is "the one registry in the entire repository
with a real, live-tested runtime consumer."

### Classification summary

| Classification | Count | Files |
|---|---|---|
| PRODUCTION DEPENDENCY | 5 | registry.py, gateway_service.py, model_registry.yaml, provider_registry.yaml, run_live_groq_smoke_test.py |
| TEST DEPENDENCY | 3 | conftest.py, test_registry.py, test_groq_live_e2e.py |
| MIGRATION TARGET (overlapping with above) | 4 | model_registry.yaml, provider_registry.yaml, probe_groq_models.py, test_registry.py |
| DOCUMENTATION | 3 | test_gateway_boundary.py, test_observation_loop_integration.py, test_tool_execution_integration.py |
| DEAD / UNUSED | 0 | none found |

---

## 2. Live Groq Path Dependency Analysis

Traced directly in code, not by inference:

```
scripts/run_live_groq_smoke_test.py (or tests/test_groq_live_e2e.py)
  1. ModelRegistry.load(CONFIG_DIR)                          <- reads config/registries/*.yaml
  2. ModelGatewayService(registry=..., router=..., adapters={"groq": GroqAdapter()})
  3. ModelRequest(...)
  4. gateway.infer(request)
       -> ModelGatewayService.infer():
            candidates = self._registry.candidates_for(request.capabilities)   <-- (A) SOLE REGISTRY DEPENDENCY
            decision = self._router.select(correlation_id, requirements, candidates, budget, routing_constraints)
                 -> CapabilityRouter.select(): pure filter/sort over the `candidates` list it was
                    handed. Zero registry awareness -- confirmed by reading
                    infrastructure/routing/capability_router.py directly, and consistent with
                    DIRECTOR_DECISION_REGISTRY.md's own finding ("no change needed to its own logic").
            self._invoke_adapter(request, decision.selected.model_id, adapter)
                 -> builds ProviderRequest, calls GroqAdapter.invoke()
                      -> real HTTPS POST to api.groq.com/openai/v1/chat/completions
                 <- ProviderResult
       <- ModelResult
```

**Exact finding:** the live path depends on the legacy registry at
**exactly one call site** — `ModelGatewayService.infer()`'s first
line, `self._registry.candidates_for(request.capabilities)`. Every
other component in the chain (`CapabilityRouter`, `GroqAdapter`, the
real Groq API call, `ModelResult` construction) is already fully
decoupled from where the candidate list came from. This was verified
by direct inspection of `capability_router.py` (it takes `candidates:
list[RoutingCandidate]` as a plain parameter with no import of, or
reference to, `ModelRegistry` anywhere in the file) and confirms
`DIRECTOR_DECISION_REGISTRY.md` §4's plan is accurate: cutover is a
**one-line change surface** at the call site, not a redesign of the
Gateway/Router/Adapter chain.

This also means: **a canonical-registry-backed replacement only needs
to produce the same `list[RoutingCandidate]` shape** that
`candidates_for()` currently produces (`model_id`, `provider_id`,
`capabilities`, `cost_class`, `availability`, `quota_remaining`) — it
does not need to replicate `ModelRegistry`'s internal YAML-loading
machinery or its `ModelRecord`/`ProviderRecord` shapes at all.

---

## 3. Canonical Replacement Map

| Legacy dependency | Current purpose | Canonical replacement | Cutover risk |
|---|---|---|---|
| `src/neptune/infrastructure/models/registry.py` (`ModelRegistry`) | Loads YAML, exposes `candidates_for()` to the Gateway | A new adapter reading from `core.registry` (Provider/Capability tables) via the Resolution layer (`ProviderResolver`, A-006), producing the same `list[RoutingCandidate]` shape | **Low**, once the adapter exists — single call-site swap (§2). **Medium** until then: the adapter itself doesn't exist yet (this is `DIRECTOR_DECISION_REGISTRY.md` §4 item 4, explicitly not yet built). |
| `config/registries/model_registry.yaml` | Data: 1 model entry | A new `Model` entity on the Postgres side (does not exist yet — `DIRECTOR_DECISION_REGISTRY.md` §4 item 1, the largest single piece of required follow-up work) | **Medium** — no per-model granularity exists in Claude A's schema today; this requires new schema, not just a data copy. |
| `config/registries/provider_registry.yaml` | Data: 1 provider entry (`groq`) | The existing `groq` entry in `06_REGISTRIES/data/providers.yaml` / Postgres `ProviderModel` (already present from A-004) | **Low** for the entry itself (already exists), **Medium** for the extra fields B's schema carries that A's lacks (`regions`, `endpoints`, `pricing_snapshot`, `quota_snapshot`, `health`, `terms_url`, `failure_history`, `fallback_providers`, `cache_characteristics` — additive schema extension, `DIRECTOR_DECISION_REGISTRY.md` §4 item 2). |
| `neptune.core.domain.capability.Capability` enum (5 of 10 values diverge from `core.registry.capability_registry.KNOWN_CAPABILITIES`) | Closed vocabulary used by `ModelRecord`/`RoutingCandidate`/`CapabilityRouter` | Union-extended `KNOWN_CAPABILITIES` on the canonical side, with `Capability` sourced from (or validated against) it (`DIRECTOR_DECISION_REGISTRY.md` §4 item 3) | **Medium** — silent-failure risk is real: a capability that only exists in one vocabulary would either fail Pydantic validation (B's closed enum) or simply never match (A's registry), and this needs resolving *before* the Model entity work, not after, or the new adapter inherits the same split vocabulary. |
| `scripts/run_live_groq_smoke_test.py` | Manual Runtime stand-in proving the live path outside pytest | Update to construct the canonical-registry adapter instead of `ModelRegistry.load()` — small, mechanical, but must not be forgotten (it is not covered by the automated test suite) | **Low**, but easy to silently miss since nothing fails loudly if this script is left unupdated — it would simply become a script that no longer runs, not a script that breaks CI. |
| `scripts/probe_groq_models.py` | Human-in-the-loop registry-refresh helper for the legacy YAML | Either delete (if the canonical registry gets its own refresh tooling from A's side) or rewrite to update the canonical registry's Model entity instead | **Low** — purely operational tooling, no test depends on it. |
| `tests/test_registry.py` | Tests the legacy registry's own correctness | Replace with an equivalent suite against the canonical adapter (same assertions: loads without error, required fields present, produces valid `RoutingCandidate`s, `CapabilityRouter` can select from them) | **Low** risk of regression if written before deletion (not after) — the assertions themselves translate almost directly. |
| `tests/test_groq_live_e2e.py` | The one test that has ever proven the real, live, end-to-end path | Must be **re-run and re-verified**, not just left alone, against the canonical adapter before cutover is considered complete — this is the single most important verification step in §5, since it is Neptune's only evidence the live path actually works with real credentials. | **High** if skipped — this is exactly the kind of regression that would only surface with a real API key in hand, not in an ordinary test run. |
| `tests/conftest.py`'s `model_registry` fixture | Shared fixture for tests 8–9 above | Either repointed at the canonical adapter, or removed once test_registry.py's replacement no longer needs it | **Low**, mechanical. |

No entries needed for `config/registries` YAML *format* itself (the
Model/Provider schema shapes) as a standalone migration item beyond
what §4 items 1–2 already cover — the format is a Pydantic model, not
a separate system to retire.

---

## 4. Provider-Independence Test Result

**Result: ADDED.** `tests/contract/test_neptune_core_provider_independence.py`
was written and passes (`1 passed`), mirroring `tests/contract/
test_core_provider_independence.py`'s exact static-AST-scan
methodology, applied to `src/neptune/core` instead of `src/core`.

**Independence from C-004, reasoned explicitly:** this is a pure
static-analysis test — it parses Python source files with `ast` and
inspects import statements. It performs no database query, reads no
registry data, and does not construct or depend on any object from
`ModelRegistry`, `core.registry.*`, or any Resolution-layer code. Its
only "dependency" is the *existence* of `src/neptune/core/*.py` files
on disk, which predates this task entirely. Nothing about registry
consolidation (C-004's evident scope, per `DIRECTOR_DECISION_
REGISTRY.md` §4's item 1 — adding a Model entity to Claude A's
registry) changes what this test checks or how. It was therefore safe
to add now, per C-005 item 4's instruction, and is fully isolated from
registry migration: it does not import, reference, or assert anything
about either registry system.

Forbidden-prefix list used (broader than the minimum "no provider
SDK" check already present in `tests/test_contracts.py` since B-004,
to match Claude A's stricter methodology exactly): `requests`,
`litellm`, `groq`, `openai`, `anthropic`, `google`, `sqlalchemy`,
`psycopg2`, `asyncpg`, `neptune.infrastructure`, `neptune.application`,
`infrastructure`, `application`, `interfaces`, and `core` (catching
any future accidental cross-lane import of Claude A's top-level
package, which does not currently exist and this test now guards
against regressing).

---

## 5. Cutover Sequence

Ordered plan for retiring the legacy registry. **Not executed as part
of this task** — provided as the migration map requested.

1. **Reconcile the capability vocabulary** (`DIRECTOR_DECISION_
   REGISTRY.md` §4 item 3) — union-extend `core.registry.
   capability_registry.KNOWN_CAPABILITIES`, then source/validate
   `neptune.core.domain.capability.Capability` against it. Must happen
   first: every later step depends on both sides agreeing what a
   capability *is*.
2. **Add the Model entity to Claude A's registry** (`DIRECTOR_
   DECISION_REGISTRY.md` §4 item 1) — new `core/registry/
   model_registry.py`, `ModelModel` ORM table, `SqlAlchemyModel
   Repository`, tests, following the existing per-entity-type pattern
   from A-003.
3. **Extend the `Provider` schema** with B's operational fields
   (`regions`, `endpoints`, `pricing_snapshot`, `quota_snapshot`,
   `health`, `terms_url`, `failure_history`, `fallback_providers`,
   `cache_characteristics`) — additive, no destructive change to
   existing rows.
4. **Migrate the data**: the one `groq-llama-3.3-70b-versatile` entry
   from `config/registries/model_registry.yaml` into the new Model
   entity; merge `config/registries/provider_registry.yaml`'s extra
   fields into the existing `groq` row rather than creating a
   duplicate.
5. **Build the canonical-registry-backed adapter** producing
   `list[RoutingCandidate]` from the (now-extended) Resolution layer —
   the single new component this whole migration exists to produce.
   Write its own test suite (replacing `tests/test_registry.py`'s
   purpose) before wiring it in.
6. **Swap the one call site**: `ModelGatewayService.infer()`'s
   `self._registry.candidates_for(...)` line (§2) — this is the actual
   cutover moment, and per `DIRECTOR_DECISION_REGISTRY.md`'s own
   sequencing note, should happen as **one change, not a partial
   one**, once step 5's adapter is verified working end-to-end in
   isolation.
7. **Re-run and re-verify `tests/test_groq_live_e2e.py`** (and
   `scripts/run_live_groq_smoke_test.py` manually) against a real
   `GROQ_API_KEY`, exactly as done for B-003. This is not optional and
   not skippable — it is the only test in the repository that has ever
   proven the live path works with real credentials, and cutover risk
   is concentrated here (§3's table, "High if skipped").
8. **Delete the legacy files**, only after step 7 passes:
   - `src/neptune/infrastructure/models/registry.py`
   - `config/registries/model_registry.yaml`
   - `config/registries/provider_registry.yaml`
   - `tests/test_registry.py` (replaced by step 5's suite)
   - `tests/conftest.py`'s `model_registry` fixture (or repoint it)
9. **Update or remove the two scripts**: rewrite
   `scripts/probe_groq_models.py` for the canonical registry (or
   delete it if A's side gets equivalent tooling) and update
   `scripts/run_live_groq_smoke_test.py` to construct the new adapter.
10. **Final verification before deletion is considered complete**: full
    suite green (`pytest -q`, all previously-passing tests still
    passing, none newly skipped for a dependency reason), the
    provider-independence test added in §4 still passing (it will not
    be affected by any of the above, but should be re-run as a sanity
    check), and a fresh `pip install -r requirements.txt` +
    `pytest --collect-only` clean run (same discipline as C-003)
    since deleting files can just as easily break collection as adding
    dependencies can.

**Sequencing dependencies:** 1 blocks 2 (vocabulary must exist before
new entity uses it); 2–3 can proceed in parallel with each other but
both block 4; 4 blocks 5; 5 blocks 6; 6 blocks 7; 7 blocks 8; 9 can
happen any time after 6; 10 is the final gate before any deletion in
8 is actually performed.

---

## 6. Risks and Blockers

| # | Risk | Severity |
|---|---|---|
| 1 | **The canonical-registry adapter (cutover step 5) does not exist yet.** This entire migration is blocked on it, and it is nontrivial (it's effectively `DIRECTOR_REVIEW_001.md`'s own recommended next milestone, the `ModelGatewayPort` bridge — though that bridge and this registry adapter are related but distinct: the Gateway bridge lets `AgentRuntime` drive B's Gateway at all; this registry adapter lets B's Gateway read from A's registry instead of its own. Both use the same `ToolPortAdapter`-style pattern, but they are two separate pieces of work.) | High — the blocking dependency for the whole migration. |
| 2 | **No Model entity exists on the canonical side today** — per-model granularity (context_limit, tool_calling, structured_output, quota, health, fallbacks, preferred_roles) is real, checked, live-tested data (B-003 fixed a real bug in it) that has no destination to migrate to until step 2 of §5 is built. | Medium-High — real, scoped work, not a blocker in principle, but nontrivial. |
| 3 | **`tests/test_groq_live_e2e.py` requires a live `GROQ_API_KEY`** to actually re-verify (§5 step 7) — the same credential-availability constraint documented back in B-003/B-DEC blockers. Cutover verification cannot be considered complete on CI alone; a human needs to provide a key at least once post-cutover, same as was needed to originally prove B-003. | Medium — process dependency, not a code risk, but genuinely blocks final sign-off. |
| 4 | **Capability vocabulary reconciliation (step 1) has a silent-failure mode if done incorrectly**: if the union extension misses a value, or if `Capability`'s validation isn't actually wired to the canonical list, a future capability could pass one side's validation and silently fail to match on the other — exactly the "hard failure mode" `DIRECTOR_DECISION_REGISTRY.md` §2.4 already identified. Must be tested explicitly (both vocabularies' full membership, round-tripped) when step 1 is implemented, not just spot-checked. | Medium. |
| 5 | **Two scripts (`run_live_groq_smoke_test.py`, `probe_groq_models.py`) are not covered by the automated test suite** and will not fail loudly if left un-updated after cutover — they will simply stop working the next time a human runs them manually. Recommend adding at minimum a `--help`/import-smoke-test-level CI check for these scripts before or during cutover, so this doesn't become a second "requirements.txt-style" silent gap (C-003's own finding). | Low-Medium — easy to prevent, easy to miss if not flagged now. |
| 6 | **This is the fourth registry-adjacent finding requiring cross-branch coordination this project** (ADR-039/040 collision fixed in B-006, second ADR-039/040-class collision fixed in C-002, third ADR-041 collision fixed at the start of this task, and now this consolidation itself). Recommend the director treat the shared-ADR-number-reservation recommendation already escalated in `DEVELOPMENT_STATE/decisions.yaml` (C-DEC-001, C-DEC-004) as a prerequisite process fix before authorizing the multi-step cutover in §5, since that work will span more of both lanes' files than any single task so far and the same collision class will very likely recur otherwise. | Medium (process, not code). |

No new blockers beyond what `DIRECTOR_REVIEW_001.md` and
`DIRECTOR_DECISION_REGISTRY.md` already identified — this audit
confirms and sharpens their findings with exact file/line-level
evidence rather than surfacing anything materially new.

---

## 7. Exact Files Expected to Change During the Eventual Cutover

**New files (canonical side, Claude A's lane — not built by this task):**
- `src/core/registry/model_registry.py`
- new ORM model + `SqlAlchemyModelRepository` under `src/infrastructure/persistence/`
- schema/migration for the new Model table and `Provider` field extensions
- new adapter (exact location TBD by whoever builds it — natural home is `src/neptune/infrastructure/models/` alongside, or replacing, the current `registry.py`) producing `list[RoutingCandidate]` from the Resolution layer

**Modified files:**
- `src/neptune/application/gateway_service.py` (§2's one call site)
- `core/registry/capability_registry.py` (`KNOWN_CAPABILITIES` union extension)
- `neptune/core/domain/capability.py` (`Capability` sourced from/validated against the reconciled vocabulary)
- `06_REGISTRIES/data/providers.yaml` or equivalent (the `groq` entry's extra fields)
- `scripts/run_live_groq_smoke_test.py`
- `scripts/probe_groq_models.py` (or deleted)
- `tests/conftest.py` (`model_registry` fixture repointed or removed)

**Deleted files (only after §5 step 7's live verification passes):**
- `src/neptune/infrastructure/models/registry.py`
- `config/registries/model_registry.yaml`
- `config/registries/provider_registry.yaml`
- `tests/test_registry.py` (replaced, not just removed)

**Tests requiring migration (write-then-delete-old, per §5 step 5):**
- `tests/test_registry.py` → equivalent suite against the canonical adapter

**Tests requiring re-verification, not migration (must still pass, content-unchanged):**
- `tests/test_groq_live_e2e.py`
- `tests/test_gateway_boundary.py`, `tests/test_observation_loop_integration.py`, `tests/test_tool_execution_integration.py` (already registry-independent via `_StubRegistry`; confirm they remain so after the swap)
- `tests/contract/test_neptune_core_provider_independence.py` (added by this task; unaffected by registry changes by design, but worth re-running as a sanity check)

**Data requiring transfer:**
- One model entry: `groq-llama-3.3-70b-versatile` (context_limit, tool_calling, structured_output, cost_class, quota, health, availability, verified_at, fallbacks, preferred_roles, notes)
- One provider entry's extra fields: `groq`'s regions, endpoints, pricing_snapshot, quota_snapshot, health, terms_url, failure_history, fallback_providers, cache_characteristics (merged into the existing canonical `groq` row, not a new row)

**Live Groq validation that must be repeated:**
- `tests/test_groq_live_e2e.py`'s three tests (`test_live_inference_round_trip`, `test_live_health_check_reports_healthy`, `test_live_model_listing_returns_data`), with a real `GROQ_API_KEY`, against the post-cutover code path — not just against the pre-cutover legacy path as was done in B-003.

# ADR-039 — Resolution Layer Provider Selection Policy

**Status:** DECISION
**Scope:** Claude A / Resource & Capability Resolution Layer (A-006)

## Decision

`ProviderResolver.resolve_provider(capability_id)` (src/core/resolution/
provider_resolver.py) selects the "best matching" provider for a
capability using a three-key deterministic sort over fields every
`Provider` record already carries:

1. **Reliability status** (`STRUCTURAL` > `BONUS` > `BURST` > `LOCAL`;
   `RETIRED` is excluded from eligibility entirely, not just ranked last)
2. **Verification status** (`verified` > `candidate` > `unverified`)
3. **provider_id, alphabetically** -- final deterministic tiebreak

No provider name, provider_type, or vendor-specific field is ever read by
the ranking. The same three keys apply identically whether the candidate
set is the five providers seeded in A-004 or any provider Claude B
registers later.

## Rationale

**Why these three keys and not something richer.** The task brief
requires "best matching registered provider" with the explicit constraint
"No hardcoded providers. No Groq-specific logic." Status and
verification_status are the only two fields in `06_REGISTRIES/
PROVIDER_REGISTRY.md`'s existing vocabulary that describe provider
*quality* in a registry-agnostic way -- everything else on a Provider
record (capabilities, depends_on, notes) describes *what* it does, not
*how good a choice* it is. Reaching for anything beyond these two would
mean inventing a new quality signal with no Bible grounding, which is out
of scope for a resolution layer that's explicitly "selection logic only."

**Why RETIRED is excluded rather than just ranked last.** A retired
provider isn't a worse choice among choices -- per `06_REGISTRIES/
PROVIDER_REGISTRY.md`'s reliability categories, RETIRED means the entry
is kept for historical/audit reasons, not because it's usable. Ranking it
last would still select it when it's the only eligible candidate, which
is wrong; filtering it out means "no eligible provider" (a real,
observable outcome) is preferred over silently returning something
retired.

**Why alphabetical id as the final tiebreak instead of, say, registration
order or an arbitrary index.** Determinism was the actual requirement
(the integration test explicitly proves the same resolution reproduces
identically across a process restart) -- alphabetical is simplest,
requires no extra bookkeeping (no "first registered" timestamp
dependency), and is trivially reproducible by inspecting the registry
data with no execution needed.

**Why unrecognized status/verification_status values sort after known
ones instead of raising.** `_STATUS_RANK.get(provider.status, 50)` and
`_VERIFICATION_RANK.get(..., 50)` degrade gracefully rather than crash
resolution if the director's vocabulary expands (as it already did once,
ADR-A-011) faster than this ranking table is updated -- an unrecognized
status just becomes a lower-priority candidate, not a fatal error.

**Why "no eligible provider" returns a ResolutionResult instead of
raising.** The brief is explicit that this layer performs "no execution,
no HTTP, no runtime actions" -- a resolution layer that can't find a
match is reporting a fact (nothing eligible right now), not failing an
operation. `ResolutionResult(provider=None, ...)` with a `reason` in
metadata lets a caller (the future Router/Runtime Intent layer) decide
what to do about it, rather than the resolution layer imposing that
decision via an exception.

**Why dependency expansion is not part of eligibility filtering.**
`resolve_provider` only expands the *selected* provider's dependency
chain (`ResourceResolver.expand_dependencies`), not every eligible
candidate's. Expanding all candidates' chains just to discard the
unselected ones would be wasted work with no informational benefit --
metadata already records every eligible candidate's id
(`eligible_provider_ids`) for a caller who wants to inspect alternatives.

## Consequences

- This policy has no notion of cost, latency, or quota -- those are
  exactly the concerns ADR-033 (one provider before multi-provider
  resilience) and the Router Contract's routing-policy layer own, not
  this resolution layer. A future Router built on top of `ProviderResolver`
  may re-rank `eligible_provider_ids` using live operational data Claude B
  supplies (rate limits, current latency) without this ADR's ranking
  needing to change -- `ProviderResolver` produces the eligible set and a
  default pick; nothing prevents a caller from choosing differently among
  `metadata["eligible_provider_ids"]`.
- A capability with multiple equally-verified STRUCTURAL providers always
  resolves to the alphabetically-first one. This is a real limitation if
  "best" should someday mean something load-balanced or cost-aware, not
  just "first, deterministically" -- explicitly deferred, matching
  ADR-038's precedent of shipping the simplest correct policy first.

## Validation

Revisit once Claude B's provider registrations carry live operational
metadata (uptime, current rate-limit headroom, measured latency) --
at that point the ranking key can grow a fourth (or replace a) component
without changing `ResolutionResult`'s shape, since `metadata` is already
open-ended.

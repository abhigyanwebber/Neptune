# Provider Candidates — Integration Evaluation (B-002)

Status: research snapshot, verified 2026-08-13. Not a commitment.
Per ADR-001/ADR-024, no provider here is an architectural dependency;
all access goes through `ProviderAdapter` (see `03_CONTRACTS/PROVIDER_CONTRACT.md`)
and registry data (see `06_REGISTRIES/integration_registry.yaml`).

Scope: Groq, OpenRouter, Gemini, Cerebras, Mistral. Fields recorded
per provider: API compatibility, free tier, tool calling, streaming,
pricing, rate limits, SDK maturity.

---

## Groq

- **API compatibility:** OpenAI-compatible REST (`/openai/v1`). Fits
  directly behind LiteLLM (ADR-032); already the B-001 vertical-slice
  candidate.
- **Free tier:** Yes, no card required.
- **Tool calling:** Yes, on `llama-3.3-70b-versatile` and
  `openai/gpt-oss-120b`.
- **Streaming:** Yes.
- **Pricing:** Free tier + separate paid per-token tier for
  volume/latency guarantees.
- **Rate limits:** Reported ~30 RPM / ~6,000 TPM / ~1,000–14,400 RPD,
  per model, free tier. Sources disagree on exact numbers (provider
  does not consistently publish one canonical table across all
  models) — treat as directional, not contractual.
- **SDK maturity:** Mature OpenAI-compatible ecosystem; already
  scaffolded in Neptune (`infrastructure/providers/groq_adapter.py`,
  B-001).
- **Verdict:** Confirmed practical first candidate. No change from
  B-001.

## OpenRouter

- **API compatibility:** OpenAI-compatible REST, single endpoint
  fronting 300+ models across many upstream providers.
- **Free tier:** Yes, no card required. A dedicated `openrouter/free`
  auto-router (launched Feb 2026) picks from the current free-model
  pool matching requested features (e.g. tool calling).
- **Tool calling:** Supported on a subset of free models; the
  `openrouter/free` router can be asked to filter for it.
- **Streaming:** Yes.
- **Pricing:** $0 for `:free`-suffixed models; BYOK mode routes
  through the caller's own provider keys; paid pay-as-you-go for
  everything else.
- **Rate limits:** Reported as **20 requests/min** consistently
  across sources. Daily cap is the volatile number — sources report
  everywhere from 50/day (no spend history) up to 200–1,000/day after
  a one-time credit purchase. **This is a genuinely moving target;
  verify live at integration time, not from this document.**
- **SDK maturity:** OpenAI-compatible; no dedicated SDK required.
  Large, active ecosystem.
- **Notable risk:** The exact free-model *roster* rotates — models
  are added/removed without much notice (multiple independent sources
  confirm this). A pipeline that hardcodes a specific `:free` model ID
  is fragile; targeting `openrouter/free` (capability-based selection)
  is more robust and maps naturally onto Neptune's capability-pinning
  principle (ADR-024).
- **Verdict:** Strong second candidate / fallback-chain member.
  Its multi-provider free pool is a natural fit for the Router's
  fallback_chain mechanism (ROUTER_CONTRACT) rather than a primary,
  since day-to-day availability of any *specific* free model is not
  guaranteed.

## Gemini (Google AI Studio / Gemini Developer API)

- **API compatibility:** Native Gemini API + REST; also has an
  OpenAI-compatibility shim on some endpoints. Not natively
  OpenAI-compatible for all features (e.g. some tool-calling shapes
  differ), so LiteLLM's Gemini adapter (not the OpenAI-compat shim) is
  the safer normalization path.
- **Free tier:** Yes for Flash-tier models, no card required —
  **but enabling billing on the Google Cloud project removes the free
  tier entirely for that project**, and sources report Gemini Pro's
  free tier was removed in April 2026. Flash and Flash-Lite remain the
  reliable free options as of this snapshot.
- **Tool calling:** Yes.
- **Streaming:** Yes.
- **Pricing:** Free tier (rate-limited) + standard paid tiers (Tier 1
  unlocked at $250 cumulative spend, per some sources).
- **Rate limits:** Reported 5–15 RPM depending on model, up to
  ~250K–1M TPM, 100–1,000 RPD. Multiple independent sources report a
  December 2025 quota *reduction* — this free tier has trended
  stricter over time, not looser.
- **SDK maturity:** Mature (`google-generativeai` / `google-genai`
  Python SDK), widely used.
- **Notable risk:** Highest policy volatility of the five candidates
  in this batch — Pro-tier free access was reportedly pulled entirely
  in the last ~6 months, and billing/free-tier interaction is a sharp
  edge (turning on billing for unrelated paid usage in the same GCP
  project silently kills the free lane).
- **Verdict:** Viable secondary/fallback candidate for its strong
  multimodal capability, but its free-tier terms are the least stable
  of the five and require the shortest re-verification interval if
  adopted.

## Cerebras

- **API compatibility:** OpenAI-compatible REST (`api.cerebras.ai/v1`).
- **Free tier:** Yes, no card required.
- **Tool calling:** Yes, standard OpenAI tool schema.
- **Streaming:** Varies by model per one source; generally supported.
- **Pricing:** Free tier + paid "Developer" tier (removes hourly/daily
  caps, per-token billing) for real agent-loop traffic.
- **Rate limits:** Sources conflict materially: one set reports
  ~5 RPM / 30K TPM / 1M TPD limited to 2 models with an 8K-token
  context cap on the free tier; another reports 15 RPM / 30K TPM /
  1M TPD with 128K context. At 5 RPM, a coding-agent loop with
  parallel tool calls will hit 429s almost immediately — free tier is
  positioned by the vendor as single-call evaluation, not sustained
  agent traffic.
- **SDK maturity:** OpenAI-compatible; mature ecosystem via
  OpenAI-shape clients.
- **Notable strength:** Fastest raw inference of the five (custom
  Wafer-Scale Engine silicon) — independent benchmarks report Cerebras
  meaningfully faster than Groq on the same model.
- **Verdict:** Best-in-class *latency* candidate, but the free-tier
  RPM ceiling (whichever of the conflicting figures is current) is
  tight enough that it fits an occasional-burst/tool-call role better
  than a primary sustained-loop provider. Good fallback-chain member
  precisely for its speed on short, latency-sensitive calls.

## Mistral (La Plateforme)

- **API compatibility:** Native REST + OpenAI-compatible endpoint
  option.
- **Free tier:** Yes — "Experiment" tier, no card required, access to
  the full model lineup (including Mistral Large/Codestral) at $0.
  Positioned explicitly by the vendor as an evaluation tier, not a
  production one.
- **Tool calling:** Yes.
- **Streaming:** Yes.
- **Pricing:** Free (Experiment) → pay-as-you-go (card required, no
  published monthly cap) → Enterprise.
- **Rate limits:** Mistral no longer publishes exact free-tier RPM
  numbers; sources describe it as "rate-limited for experimentation"
  with a rough ~1B-token/month ceiling reported by some (unverified
  against primary docs at time of writing — the account dashboard is
  the only authoritative source once a key exists).
- **SDK maturity:** Mature; official Python/TS SDKs, active
  development, EU data residency as a differentiator.
- **Verdict:** Reasonable European/GDPR-oriented fallback candidate.
  The undocumented exact rate limit is a real evaluation gap — cannot
  be fully verified without provisioning a key and reading the live
  Admin Console limits page, which is out of scope for this
  evaluation task.

---

## Cross-Provider Notes

- All five providers are OpenAI-compatible or near-compatible, which
  keeps every one of them compatible with the existing LiteLLM
  boundary from ADR-032 without a bespoke wire-protocol adapter.
- None of the five free tiers should be treated as permanent or
  load-bearing on their own — every source set independently confirms
  free-tier terms and rosters shift over months, not years. This
  reinforces (not changes) Neptune's existing resource-economics
  posture: free tiers are genuine $0 baseline, but the Router's
  fallback-chain and the registry's `verified_at` re-check discipline
  are load-bearing, not any single provider's goodwill.
- Recommended primary + fallback ordering, for the Router's
  candidate list, is proposed in `06_REGISTRIES/integration_registry.yaml`.

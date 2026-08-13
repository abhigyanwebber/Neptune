# Sandbox Candidates — Integration Evaluation (B-002)

Status: research snapshot, verified 2026-08-13.

Scope: Docker, E2B, Daytona, Modal, local execution. Fields recorded:
cost, isolation, self-hostability, free tier, complexity.

---

## Docker (local/self-hosted containers)

- **Cost:** $0 compute cost beyond whatever host it runs on
  (developer machine, free-tier VM, self-hosted server). No vendor
  billing at all.
- **Isolation:** Namespace/cgroup isolation — meaningfully weaker than
  a microVM (E2B/Firecracker) against a genuinely hostile workload,
  but standard and well-understood; can be hardened (seccomp,
  read-only rootfs, no-new-privileges, network policy) without
  changing vendor.
- **Self-hostability:** Full — this *is* the self-hosted option.
- **Free tier:** N/A (not a hosted product); cost is host compute.
- **Complexity:** Low to run one container; moderate to operate
  reliably at scale (orchestration, image lifecycle, resource limits).
- **Verdict:** The genuine $0-baseline sandbox. Best fit for local
  development, low-volume production, and as the reference isolation
  layer that every managed alternative below should be benchmarked
  against for cost.

## E2B

- **Cost:** Per-second billing on vCPU + RAM, ~$0.0504/vCPU-hour,
  ~$0.0162/GiB-hour (rates match Daytona's raw compute pricing almost
  exactly). Hobby tier: one-time $100 usage credit (not renewing —
  burst capital per Neptune's own resource classification), 20
  concurrent sandboxes, 1-hour max session, no card required. Pro:
  $150/month floor for 24-hour sessions, 100 concurrent sandboxes.
- **Isolation:** Dedicated Firecracker microVM per session — the
  strongest isolation of the managed options surveyed, meaningfully
  above container-only isolation for untrusted/agent-generated code.
- **Self-hostability:** Yes — sandbox infrastructure is Apache-2.0 and
  self-hostable, at the cost of real operational effort (running your
  own Firecracker fleet).
- **Free tier:** Yes, but framed as a one-time credit, not a
  recurring free allowance — this is burst capital under Neptune's
  own economic classification (03_RESOURCE_LAYER / RESOURCE_ECONOMIC_
  CLASSIFICATION.md), not a $0 baseline.
- **Complexity:** Low integration complexity (polished SDK, "path of
  least resistance" per one source for code-execution-style agent
  loops); self-hosting raises complexity substantially.
- **Verdict:** Best isolation-per-integration-effort of the managed
  options. Right tool when the workload is genuinely untrusted
  (executing arbitrary agent-generated code) and the $100 one-time
  credit or a metered budget is acceptable — not a $0-baseline
  component on its own.

## Daytona

- **Cost:** No monthly base fee; pay-as-you-go per second from a
  reported $200 free compute credit (also burst capital, not
  recurring).
- **Isolation:** Container-based by default (shared-kernel), with
  optional Kata/Sysbox for stronger, closer-to-microVM isolation when
  needed — weaker default isolation than E2B unless the stronger mode
  is explicitly configured.
- **Self-hostability:** **Materially degraded since the Bible's likely
  original research window.** Multiple independent sources report
  Daytona's open-source repository stopped accepting outside
  contributions around June 2026 and moved core development to a
  private codebase; one source describes it as effectively closed
  source now. A self-hosted deployment today would not track new
  upstream features.
- **Free tier:** $200 one-time credit (burst capital, same caveat as
  E2B).
- **Complexity:** Low for the managed product (sub-second/sub-100ms
  cold starts is the headline feature); self-hosting is no longer a
  reliable path given the repo status above.
- **Verdict:** **Downgraded relative to what the Bible's candidate
  research likely assumed.** The open-source/self-hostable story that
  would have made Daytona attractive under Neptune's replaceability
  principle no longer holds as of this snapshot. Still usable as a
  managed product, but not as a self-hostable fallback.

## Modal

- **Cost:** Serverless, per-second billing; competitive-to-cheapest on
  pure CPU sandboxes among the managed options surveyed.
- **Isolation:** Managed sandbox isolation (not deeply detailed in
  sources beyond "isolated"); the standout feature is not isolation
  strength but **GPU-in-sandbox** — the only option in this set where
  a sandbox can hold a GPU for inference/fine-tuning inside the same
  isolated process as tool calls.
- **Self-hostability:** No — fully managed, no self-host path
  identified in sources.
- **Free tier:** Not clearly documented as a no-card free tier in the
  sources gathered; treat as paid-only pending direct verification.
- **Complexity:** Low integration complexity for Python-centric
  workloads; reported autoscaling to very high concurrency.
- **Verdict:** Not relevant to Neptune's near-term needs (Neptune's
  Stage 2-3 scope is text/tool-call agent execution, not GPU
  inference inside the sandbox). Worth revisiting only if/when Neptune
  needs to run models or heavy compute *inside* the sandboxed
  execution context itself, which is out of scope today.

## Local execution (no sandbox — direct host process)

- **Cost:** $0.
- **Isolation:** None beyond OS user permissions. Only appropriate for
  fully trusted code/tool calls (e.g. Neptune's own test suite, not
  arbitrary agent-generated shell commands).
- **Self-hostability:** N/A — it's already local.
- **Free tier:** N/A.
- **Complexity:** Lowest possible.
- **Verdict:** Reasonable for Neptune's own CI/dev-loop tooling and
  for tools explicitly marked as safe/no-isolation-required by the
  Permission boundary, but not a substitute for a real sandbox once
  Neptune executes agent-proposed, untrusted commands — which is
  exactly the scenario SANDBOX_CONTRACT exists to cover.

---

## Cross-Sandbox Notes

- **Isolation strength ranking (strongest → weakest) as surveyed:**
  E2B (Firecracker microVM) > Daytona-with-Kata/Sysbox-enabled >
  Docker (namespaces/cgroups) ≈ Daytona-default-container >
  local execution (none).
- **Self-hostability ranking, current status:** Docker (full) > E2B
  (Apache-2.0, self-hostable with real ops effort) > Daytona
  (degraded — repo effectively closed as of June 2026) > Modal (none
  identified).
- **$0-baseline fit:** Docker and local execution are the only two
  options that are genuinely free on an ongoing basis rather than
  "free" via a one-time credit. E2B/Daytona's free tiers are burst
  capital per Neptune's own resource classification and should be
  budgeted as such, not treated as part of the durable baseline.
- **Recommendation basis** for the final stack selection: see
  `06_REGISTRIES/integration_registry.yaml`.

# MCP Candidates — Integration Evaluation (B-002)

Status: research snapshot, verified 2026-08-13.

Scope: Official MCP, FastMCP, Open MCP ecosystems. Fields recorded:
stability, adoption, adapter complexity.

---

## Official MCP (Model Context Protocol)

- **What it is:** Anthropic-originated, now vendor-neutral protocol
  for connecting AI applications (clients) to tools/data (servers) via
  a standard JSON-RPC 2.0-based client-server architecture. Donated to
  the Agentic AI Foundation under the Linux Foundation (December
  2025) — governance is no longer single-vendor.
- **Stability:** The stable spec at the start of this evaluation
  window was dated 2025-11-25. A **2026-07-28 release candidate**
  (stateless protocol core, Extensions framework, Tasks, MCP Apps,
  authorization hardening, a formal deprecation policy) went through a
  ten-week validation window and **the final 2026-07-28 spec has since
  shipped**, per the protocol's own blog. The spec now has an explicit
  SDK tier system and a conformance suite gating "Standards Track"
  changes — meaningfully more process maturity than a year prior.
  Practical implication for Neptune: target the 2026-07-28 spec, but
  expect at least one more comparable revision cycle; do not treat any
  single spec version as permanently frozen the way Neptune's own
  ADRs are.
- **Adoption:** Very high and independently corroborated across
  multiple sources: 97M+ monthly SDK downloads (TypeScript + Python
  combined), both crossing 1B total downloads; official adoption by
  OpenAI, Google DeepMind/Gemini, Microsoft Copilot Studio, AWS; over
  10,000 active public servers per Anthropic's own count, with
  registry/GitHub-topic counts in the 10-20K range depending on
  methodology. One enterprise survey (Stacklok) puts *production*
  usage at 41% of surveyed orgs — real, but not universal; treat
  higher "78% adoption"-style figures found elsewhere as unsourced.
- **Adapter complexity:** Low. Official SDKs exist for Python,
  TypeScript, Java, Kotlin, C# (maturity varies by language — verify
  before depending on a non-Tier-1 SDK). This is the layer Neptune's
  own `03_CONTRACTS/TOOL_CONTRACT.md`-facing MCP integration should
  target directly, not a third-party wrapper.
- **Verdict:** The protocol itself is the correct integration target.
  It is infrastructure-grade at this point (governance, download
  volume, multi-vendor backing), not a risky bet.

## FastMCP

- **What it is:** The high-level Python API (published as `mcp[cli]`
  on PyPI) that implements MCP server-building ergonomics on top of
  the official protocol — handles protocol/transport details so
  server authors define tools/resources/prompts directly.
- **Stability:** Tracks the official Python SDK; described in sources
  as the standard way to build an MCP server in Python, not a
  competing/fragile alternative implementation.
- **Adoption:** High within the Python MCP-server-building community;
  cited as the reference implementation pattern in most 2026 MCP
  guides surveyed. Individual servers built with it (e.g. a popular
  memory-manager server) show real install/usage numbers, evidence
  the pattern is in active production use, not just documentation
  examples.
- **Adapter complexity:** Low — this *is* the low-complexity path for
  Python server authors, which matches Neptune's Python implementation
  language (confirmed in B-001).
- **Verdict:** Correct default for any MCP *server* Neptune builds
  in-house. Not a separate ecosystem from official MCP — it is the
  official Python SDK's high-level API, so adopting it carries no
  extra lock-in beyond adopting MCP itself.

## Open MCP Ecosystems (registries, third-party servers, marketplaces)

- **What it is:** The broader server catalog — official MCP Registry
  (in preview, ~9,600+ "latest" server records per a May 2026 API
  pull), Glama's registry (19,800+ indexed), GitHub's `mcp-server`
  topic (~16,000 repos), plus product-embedded marketplaces (e.g.
  Cline's MCP marketplace, noted in `tool_candidates.md`).
- **Stability:** Highly variable by individual server — this is an
  open ecosystem, not a single governed artifact. The protocol layer
  is stable; individual third-party servers carry the normal
  open-source risk profile (abandonment, quality variance, unaudited
  security posture).
- **Adoption:** Large in aggregate (headline counts above), but
  concentration matters more than the total: a handful of
  infrastructure-vendor servers (Cloudflare's MCP server covering
  ~2,500 API endpoints in ~1K tokens is cited as a notable, well-
  engineered example) carry disproportionate real usage versus the
  long tail.
- **Adapter complexity:** Low per-server (any conformant MCP server
  plugs into a conformant MCP client without custom code), but
  **evaluation complexity per server is non-trivial** — Neptune should
  not treat "it's an MCP server" as a safety or quality signal on its
  own; each third-party server Neptune actually wires in needs its own
  PERMISSION_CONTRACT-level review, same as any other external tool.
- **Verdict:** Use the open ecosystem as a *source* of candidate tools
  to evaluate individually, not as a blanket-trusted dependency tier.
  The protocol's adoption and governance justify building on MCP
  itself; it says nothing about the trustworthiness of any specific
  third-party server pulled from a registry.

---

## Summary

| Layer | Stability | Adoption | Adapter complexity |
|---|---|---|---|
| Official MCP protocol | High, Linux Foundation-governed, versioned spec with conformance suite | Very high, multi-vendor | Low (official SDKs) |
| FastMCP (Python SDK) | Tracks official SDK | High in Python ecosystem | Low |
| Open MCP ecosystem (3rd-party servers) | Variable per-server | Large in aggregate, concentrated in practice | Low to wire in, non-trivial to vet |

**Recommendation:** Neptune's MCP integration (already anticipated in
the Bible's Agent/Harness → Tools/MCP → External systems dependency
chain) should target the official protocol via its Python SDK/FastMCP
directly. Third-party servers from the open ecosystem are a tool
*supply*, evaluated case-by-case through the same Tool/Permission
boundary as any other integration — not a separate trust tier.

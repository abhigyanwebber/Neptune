# Tool-Layer Candidates — Integration Evaluation (B-002)

Status: research snapshot, verified 2026-08-13.

Scope: OpenHands, Aider, Cline, Roo (Roo Code), Goose, Codex CLI,
Gemini CLI. Classification per director instruction:

- **A — Directly reusable:** can be integrated close to as-is behind
  Neptune's Tool/Sandbox/Permission boundaries.
- **B — Reusable with adapter:** core logic/patterns are sound, but
  needs a Neptune-side adapter to fit TOOL_CONTRACT/PERMISSION_CONTRACT.
- **C — Pattern only:** not integrated as code; study the architecture,
  reimplement inside Neptune's boundaries.
- **D — Reject:** not viable for this evaluation window.

**Important status changes since the Bible's original candidate
research:** two of the seven named candidates are no longer viable as
living upstream dependencies as of this snapshot:

- **Roo Code was archived in May 2026** (multiple independent sources).
  It is a hard fork of Cline; its patterns (multi-agent "modes":
  Architect/Code/Debug/Custom) are still worth studying, but there is
  no upstream to track.
- **Gemini CLI is being retired June 18, 2026** in favor of a
  closed-source successor, per the same source set. Its patterns
  remain instructive; the project itself is not a dependency target.

---

## OpenHands

- **What it is:** Autonomous, sandboxed coding agent. Three surfaces:
  SDK (build custom agents), CLI, cloud platform. Runs headless in CI.
  Docker-based runtime for isolated execution by design.
- **License:** MIT.
- **Scale/momentum:** ~75-80K GitHub stars, $18.8M Series A — one of
  the most active projects in this set.
- **Architecture fit:** Its SDK-first design and Docker-native sandbox
  model line up unusually well with Neptune's Agent/Harness +
  Sandbox-boundary split — it already separates "agent loop" from
  "execution runtime" the way Neptune's contracts require.
- **Classification: B — Reusable with adapter.** The agent-loop/runtime
  split is directly usable as a reference implementation for Neptune's
  own tool-execution + sandbox integration, but OpenHands' own
  permission/approval model is not Neptune's PERMISSION_CONTRACT and
  would need to sit behind a Neptune adapter rather than being used
  verbatim as the source of truth for permission decisions.

## Aider

- **What it is:** Git-native terminal pair-programming agent. Commits
  directly to Git; provider-agnostic (100+ providers via LiteLLM).
- **License:** Apache-2.0.
- **Scale/momentum:** Very high real-world usage (one source reports
  15B tokens/week across 6.8M installs); mature, stable, narrow scope
  by design (surgical Git edits, not full autonomy).
- **Architecture fit:** Already uses LiteLLM internally — same
  normalization layer Neptune committed to in ADR-032. Its Git-commit
  discipline is a useful pattern for Neptune's own checkpointing.
- **Classification: B — Reusable with adapter** for the specific
  "propose diff → git commit" tool pattern; **C — Pattern only** for
  everything else. Aider is intentionally a narrow, single-purpose
  tool rather than a general harness, so it's a strong reference for
  one tool implementation (git-native code edit) rather than a
  candidate for wholesale integration as Neptune's tool layer.

## Cline

- **What it is:** Model-agnostic agent spanning IDE (VS Code), CLI,
  and SDK. Plan/Act mode with step-by-step human approval; permissioned
  file/terminal/browser/MCP access; MCP marketplace built in.
- **License:** Apache-2.0 (core); JetBrains plugin is closed-source —
  license is not uniform across the whole product surface.
- **Scale/momentum:** ~57-65K stars, largest reported user base (one
  source: 4M+ developers) of the IDE-native tools in this set.
- **Architecture fit:** The Plan/Act approval-gate pattern is close in
  spirit to Neptune's PERMISSION_CONTRACT ("tool availability does not
  grant permission" — the model proposes, a boundary approves). Its
  built-in MCP marketplace is directly relevant to B-002's MCP
  evaluation below.
- **Classification: B — Reusable with adapter.** Governance/approval
  model is the closest philosophical match to Neptune's permission
  boundary of anything surveyed; worth adapting rather than
  reimplementing from scratch. Full IDE-extension surface is out of
  scope for Neptune's harness (Neptune is not building a VS Code
  extension), so only the agent-loop + approval-gate + MCP-client
  layers are the reusable slice, not the IDE integration.

## Roo (Roo Code)

- **What it is:** A Cline fork adding multi-agent "modes" (Architect,
  Code, Debug, Custom).
- **License:** Was Apache-2.0-family (inherited from Cline lineage).
- **Status: ARCHIVED, May 2026.** No longer an actively maintained
  upstream.
- **Classification: C — Pattern only.** The multi-mode concept
  (specializing agent behavior/tools per phase of work: architect vs.
  implementer vs. debugger) is a legitimate pattern worth studying for
  Neptune's eventual multi-agent capability (explicitly a "later"
  item per the Bible), but there is no live project to integrate or
  track. Do not add as a dependency.

## Goose

- **What it is:** Editor-agnostic autonomous agent for code plus
  adjacent work (research, file processing, workflows, GitHub
  automation) — broader scope than a pure coding agent.
- **License:** Apache-2.0.
- **Governance:** Moved under the Linux Foundation / Agentic AI
  Foundation in 2026 — notable for long-term stability, since it
  removes single-vendor risk from the project's future.
- **Architecture fit:** Broader task scope than Aider/Cline maps
  reasonably well onto Neptune's eventual ambition beyond pure coding
  (the Bible's "eventually long-running and multi-agent capabilities").
- **Classification: B — Reusable with adapter.** Foundation governance
  makes it a comparatively low-risk long-term dependency if Neptune
  later wants a broader-than-coding tool surface; for now, treat as a
  pattern/reference alongside OpenHands rather than adopting code
  directly, since B-002 is evaluation-only.

## Codex CLI (OpenAI)

- **What it is:** Terminal-first coding agent. Dual-language: a thin
  Node.js/TypeScript launcher shim over a Rust core (60+ crates:
  CLI, TUI, core logic, sandboxing, auth, MCP). Config-layered
  (system → user → project → CLI flags), explicit `sandbox_mode`
  (`workspace-write`, etc.) and `approval_policy` settings. Supports
  MCP servers with parallel tool calls.
- **License:** Apache-2.0, open source (github.com/openai/codex).
- **Scale/momentum:** ~75K stars, extremely high release cadence
  (700+ releases by one snapshot) — very actively developed.
- **Architecture fit:** The Rust core's explicit sandbox_mode +
  approval_policy separation is architecturally close to Neptune's
  own Sandbox/Permission contract split — arguably the cleanest
  reference implementation of that boundary among the seven
  candidates, because it's implemented as two genuinely separate
  concerns rather than one blended approval flow.
- **Classification: B — Reusable with adapter** for the sandbox/
  approval-policy design pattern specifically; **C — Pattern only**
  for the rest (it is otherwise tightly coupled to OpenAI's account/
  billing model, which Neptune should not adopt as a dependency).

## Gemini CLI (Google)

- **What it is:** Google's terminal coding agent.
- **Status: being retired June 18, 2026**, replaced by a closed-source
  successor, per the source set gathered for this evaluation.
- **Classification: D — Reject** as an integration target. Its
  patterns are not distinctive enough relative to Codex CLI/OpenHands
  to justify separate study given the project's own imminent
  retirement; noting its existence and status for the record is
  sufficient.

---

## Summary Table

| Tool | License | Status | Classification |
|---|---|---|---|
| OpenHands | MIT | Active, well-funded | B |
| Aider | Apache-2.0 | Active, very high usage | B (narrow scope) / C |
| Cline | Apache-2.0 (core) | Active, largest user base | B |
| Roo Code | Apache-2.0-family | **Archived May 2026** | C |
| Goose | Apache-2.0 | Active, Linux Foundation | B |
| Codex CLI | Apache-2.0 | Active, very high cadence | B (sandbox pattern) / C |
| Gemini CLI | — | **Retiring June 2026** | D |

No candidate in this set is classified **A (directly reusable)**.
This is an expected outcome, not a gap: every one of these tools is a
complete end-user product (its own CLI/IDE surface, its own
config/auth model, its own approval UX) rather than a library designed
to be embedded inside another harness. Neptune's actual reuse
opportunity is architectural-pattern and tool-adapter reuse (OpenHands'
sandboxed runtime split, Cline's approval-gate model, Codex CLI's
sandbox_mode/approval_policy separation), not wholesale adoption of
any one product as Neptune's tool layer.

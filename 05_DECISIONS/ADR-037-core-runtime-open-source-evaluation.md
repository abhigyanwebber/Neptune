# ADR-037 — Open-Source Harness Integration Evaluation (Core Runtime)

**Status:** DECISION
**Scope:** Claude A / Core Agent Runtime & Execution Control (this stage only)

## Decision

No open-source harness code is directly integrated or adapted (copied/ported)
into the Core Runtime at this stage. Architectural patterns are used as
reference only. This is a "C" (reference) outcome for every system
evaluated against Core's specific scope, not an "A" or "B" outcome.

## Why direct integration/adaptation does not apply here

The director's INTEGRATE -> ADAPT -> BUILD principle is real and already
shaped Neptune's frozen architecture (ADR-016 hybrid loop, ADR-012
event-first, ADR-018 deferred tools all trace to 04_RESEARCH/01_HARNESS_
REPORT_NOTES.md). But Claude A's current scope is narrowly the **durable
control-plane orchestration layer** -- lifecycle machinery that calls out to
a Model Gateway and Tool boundary through Protocols, with no provider SDKs,
no tool executors, no sandboxing, no UI. None of the surveyed systems ship a
reusable component at that exact boundary in a form separable from their
own provider/tool/UI code:

- Aider, Codex CLI, Gemini CLI, Cline/Roo/Kilo, Goose are complete,
  self-contained harnesses: loop + tools + provider clients + UI/CLI fused
  together. Their control-plane logic is not exposed as a standalone,
  importable library with the persistence-and-provider-independence
  boundary Neptune's contracts require (ADR-001, ADR-009,
  02_ARCHITECTURE/02_DEPENDENCY_DIRECTION.md). Extracting just the loop
  would mean re-deriving that boundary anyway, at which point it is not
  "integration," it is a rewrite with extra steps.
- OpenHands is the one system with genuine event-stream + runtime
  abstraction as a library boundary (see 04_RESEARCH/01_HARNESS_REPORT_
  NOTES.md section 12.2). It is the strongest **C (reference)** candidate:
  its EventStream pattern (every state transition is an immutable,
  replayable event) is architecturally close to what this stage
  implements. Its actual runtime/sandbox code is out of scope for Core
  (belongs to Claude B's infrastructure lane at best, and even there,
  OpenHands' Docker-runtime assumptions are heavier than Neptune's
  free/cheap-first target per ADR-034).

## Evaluation by system (A/B/C/D)

| System | Classification | Reasoning |
|---|---|---|
| OpenHands | C — reference | Event-stream architecture pattern informs this stage's event-per-transition design. MIT license (would permit direct use later if a concrete extraction target existed). Runtime/sandbox layer is Claude B's concern, not Core's, and is heavier-weight than Neptune's Stage-appropriate footprint. |
| Aider | C — reference | Git-native "repo as memory" model doesn't apply to Core (Neptune already has Postgres-backed durable state per ADR-030/ADR-009). Its clean orchestrator-over-models separation (loop vs. edit-format vs. provider layer) is a useful structural reference for keeping the Model Gateway boundary thin. Apache-2.0. |
| Codex CLI | C — reference | Plan-then-execute-with-checkpoints pattern reinforced the hybrid-loop decision (ADR-016) already made before this stage. Its OS-level sandbox is Claude B/infrastructure scope, not Core. Apache-2.0 for the CLI shell; tuned toward a proprietary model. |
| Gemini CLI | D — not reused | Free-tier/cost story is orthogonal to Core's job (LLM-supply concern, already traced into ADR-032/provider registry work, not runtime control-plane). No architectural mechanism here that isn't already covered by Aider/OpenHands/Codex CLI reference points. |
| Cline / Roo / Kilo | C — reference | Mode-based permission groups (Plan/Act) are a useful reference for how the future Tool/Permission boundary might express modes, but that boundary is explicitly out of Core's scope this stage (director: "Do not implement... tool executors... sandbox"). |
| Goose | D — not reused | MCP-native general-agent-shell orientation is a Claude B / tool-layer concern (MCP integration is explicitly excluded from this stage). No Core-runtime-specific mechanism identified beyond what OpenHands/Codex CLI already cover. |

No system reached "A — direct integration" because Core Runtime's
persistence-and-provider-independence boundary is Neptune-specific: it did
not exist as an off-the-shelf, license-clean, extractable component in any
surveyed project. No system reached "B — adaptation" (porting/rewriting a
recognizable chunk of their code) for the same reason -- there was no
component whose *code*, as opposed to its *pattern*, was worth adapting at
this layer.

## Licensing note

Nothing was copied. All classifications above are architectural-pattern
references only, so license compatibility (OpenHands MIT, Aider Apache-2.0,
Codex CLI Apache-2.0 shell, Gemini CLI Apache-2.0, Cline/Roo Apache-2.0,
Kilo MIT-family, Goose Apache-2.0 -- per 04_RESEARCH/01_HARNESS_REPORT_
NOTES.md section 12.1/12.2) is recorded for completeness, not because code
provenance needs to be tracked for this stage's deliverable.

## Validation

Revisit this ADR if a later stage (Model Gateway, Tool/Permission layer,
sandbox) finds a genuinely extractable, license-compatible component --
e.g. Aider's edit-format layer for the eventual tool layer, or OpenHands'
runtime abstraction for Claude B's sandbox work. Those are out of Core's
scope and belong to their own ADRs when that stage begins.

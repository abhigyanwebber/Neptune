# ADR-046 — ModelGatewayAdapter Tool Definitions Injected at Construction (B-009 Finding)

**Status:** PROPOSED

## Context
B-009 required proving a real Groq model deciding to call a real tool,
through the real `AgentRuntime`/`RuntimeDriver` loop. Live testing
immediately hit a blocking defect: `ModelGatewayAdapter._translate_request()`
(B-008) never populated `ModelRequest.tools` at all, because Core's
context dict (`core/runtime/context.py::assemble_context()`) carries no
"available tools" concept -- it produces `{task_id, session_id,
agent_id, task_status, requirements, constraints, recent_events}`,
nothing else.

With `ModelRequest.tools` always empty, `GroqAdapter` never sent a
`tools`/`tool_choice` payload -- yet the real model (`openai/gpt-oss-120b`,
a reasoning model) attempted a tool call anyway, without ever having
seen a tool schema. Groq's API correctly rejected this: `400 Tool
choice is none, but model called a tool`. This masked the real defect
as a provider-error at first glance; the actual root cause was upstream
of Groq entirely.

## Decision
`ModelGatewayAdapter.__init__()` now accepts an optional
`tool_definitions: list[ToolDefinition] | None` parameter. Whatever is
passed there is included in every `ModelRequest.tools` the adapter
builds, for the lifetime of that adapter instance. Absent, it defaults
to `[]` (identical to the pre-B-009 behavior, so nothing that doesn't
opt in is affected).

The caller constructing `ModelGatewayAdapter` (a script, a test, or
eventually a Runtime bootstrap routine) is responsible for knowing
which tools are actually registered with the paired `ToolPortAdapter`/
`ToolExecutor` and passing the matching `ToolDefinition`s.

## Rationale
- **Checked whether the existing contract already supported this**
  (per B-008/B-009's shared "Architectural Discipline" instruction):
  it does not, and cannot without a Core change -- `ModelGatewayPort`'s
  opaque dict has no tool-schema field, and `core/runtime/context.py`
  builds that dict from Task/constraints/events alone.
- **Prefer an adapter over changing Core** (same instruction): the fix
  lives entirely in `ModelGatewayAdapter`'s own construction, mirroring
  how it's already told `task_id`/`session_id` at construction rather
  than expecting Core to supply them per-call. No `core/*` file was
  touched.
- **Not a mere implementation detail**: without this, real tool-calling
  through the real Runtime path was structurally impossible, not just
  buggy -- the model could never have been given a tool schema to call
  correctly, regardless of prompting. That is why this is recorded as
  an ADR rather than folded into ADR-045's error-mapping fix.

## Consequences
- Whoever wires up `ModelGatewayAdapter` for a real, multi-tool
  Runtime must keep its `tool_definitions` list in sync with whatever
  `ToolRegistryAdapter` the paired `ToolPortAdapter` actually serves --
  there is no automatic discovery between the two adapters today. A
  mismatch (offering a tool definition the `ToolExecutor` doesn't
  actually have registered) would surface as a `NOT_FOUND` `ToolResult`
  outcome (B-004), not silently.
- If Core's context dict is ever extended to carry available-tools
  information itself (a genuine Core-side capability Neptune doesn't
  currently have visibility into or authority over), this adapter-level
  workaround becomes redundant and could be simplified -- not required
  to be removed, since per-adapter tool scoping may still be useful
  even then.
- The same gap could in principle affect any future `ModelGatewayPort`
  implementation, not just this one -- worth flagging for whoever
  eventually builds a second one.

## Validation
Revisit if Core's context dict gains a native tool-availability
concept, or if a Runtime bootstrap routine needs to change which tools
an adapter offers mid-lifetime rather than only at construction.

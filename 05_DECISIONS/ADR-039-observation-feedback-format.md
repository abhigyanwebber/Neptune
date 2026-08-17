# ADR-039 — Observation Feedback Format

**Status:** PROPOSED

## Decision
A ToolResult is converted to a model-visible observation as a single
`ContextMessage` with:

- `role = "tool"`
- `name = tool_result.tool_name`
- `content` = one of two deterministic, human-readable templates:

**Success** (`outcome == SUCCESS` and `output is not None`):
```
Tool {tool_name} returned:
{output as JSON, keys sorted}
```

**Failure** (`ERROR`, `TIMEOUT`, `NOT_FOUND`, or malformed success):
```
Tool {tool_name} failed ({outcome}): {error_message or "no error message provided"}
```

A malformed result -- `outcome == SUCCESS` with `output is None`, which
a correctly-behaving ToolExecutor (B-004) never actually produces --
is handled defensively with its own sentence rather than crashing or
silently emitting an empty observation.

The observation message is appended to the *end* of the previous
request's `context` list to build the follow-up `ModelRequest`
(`ObservationProcessor.build_follow_up_request`). A fresh
`correlation_id` is assigned to the follow-up request since it is a
new inference call; `task_id`/`session_id`/`turn_id` are carried
forward unchanged.

## Rationale
- **Deterministic:** `json.dumps(..., sort_keys=True)` guarantees
  identical output for identical data regardless of dict insertion
  order, so the same ToolResult always produces byte-identical
  observation text -- required for reproducible tests and for any
  future caching/checkpointing layer that hashes context.
- **Plain natural-language template, not a structured envelope:** the
  model consumes this as ordinary conversation text (role="tool" is
  the OpenAI-style convention already used elsewhere in the codebase
  for tool messages -- see ProviderRequest.messages). A minimal
  "Tool X returned:\n<json>" phrasing is unambiguous to a model
  without inventing a second, Neptune-specific schema the model would
  need to be taught.
- **Success/failure share one method surface, not one template:**
  distinguishing "returned:" vs "failed (...):" lets a model reliably
  tell success from failure by string shape alone, without needing to
  parse embedded status fields.
- **role="tool" reuses an existing core type** (`ContextMessage` from
  `model_gateway.py`) rather than inventing a new observation-specific
  message type, keeping the loop provider-independent and consistent
  with how tool_definition/tool_intent already flow through the
  Gateway boundary.

## Consequences
- Provider adapters that expect a different tool-result message shape
  (e.g. structured `tool_call_id`-keyed JSON blocks, as OpenAI's actual
  API expects) will need their own translation from this
  `ContextMessage` into their wire format -- this ADR only fixes
  Neptune's *internal* representation, not any specific provider's
  wire protocol. (GroqAdapter's current `invoke()` sends
  `ContextMessage.role`/`.content` directly; a future task should
  verify Groq's OpenAI-compatible endpoint accepts a plain
  `role: "tool"` message this way, or add the `tool_call_id`
  linkage it may require.)
- The exact template strings are an implementation detail Neptune
  controls entirely and can change without touching any frozen
  contract -- `ContextMessage.content` is an opaque string as far as
  MODEL_CONTRACT/PROVIDER_CONTRACT are concerned.
- Observation text size is not separately bounded here; it inherits
  whatever bound was already placed on the underlying ToolResult.output
  by ToolExecutor's `max_output_bytes` (B-004).

## Validation
This decision must be revisited if a real provider's tool-result
message format requires more structure than a single free-text
`ContextMessage` (e.g. explicit `tool_call_id` linkage), or if
multiple tool calls per turn need to be distinguished in a way plain
sequential text messages cannot express.

## Renumbering note
Originally filed as ADR-037. Renamed to ADR-039 during B-006's
worker/claude-a merge, since Claude A had independently claimed
ADR-037 (core-runtime-open-source-evaluation.md) and ADR-038
(runtime-driver-policy.md) on the unmerged branch -- a real number
collision discovered only because this merge finally brought both
ADR sequences into the same working tree. No content changed besides
the number and this note.

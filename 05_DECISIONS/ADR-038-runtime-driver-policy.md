# ADR-038 — Runtime Driver Execution Policy

**Status:** DECISION
**Scope:** Claude A / Core Runtime Driver Layer (A-005)

## Decision

`RuntimeDriver` (src/core/runtime/driver.py) implements the simplest
policy that satisfies the director's brief: after each `AgentRuntime.
run_turn()` call, look only at whether the resulting Turn made tool calls
and whether any of those calls failed, then choose one of three actions --
continue, complete, or stop. No planning, no retries, no multi-signal
heuristics, no provider-specific response parsing.

```
turn = runtime.run_turn(session_id)
if tool_failed(turn):        -> STOPPED_TOOL_FAILURE
elif should_complete(turn):  -> complete_task(), COMPLETED
elif should_continue(turn):  -> loop again
else:                        -> break (unreachable today; see below)
# turn_index >= max_turns at any point -> STOPPED_MAX_TURNS
```

## Rationale

**Why turn.tool_calls is the only signal.** AgentRuntime.run_turn()
already fully resolves one round of model-request -> tool-execution ->
observation before returning (engine.py's `_MAX_TOOL_ROUNDS_PER_TURN`
bounds that internal loop). By the time the driver sees a completed Turn,
the only externally-observable fact distinguishing "the model is still
working" from "the model is done" is whether it asked for tools this
turn. Using anything richer (parsing `model_response.content` for
natural-language completion phrases, checking a provider-specific
`finish_reason` field, etc.) would either (a) require provider-specific
assumptions the director's brief explicitly forbids, or (b) require a
real Model Gateway to validate against, which doesn't exist yet
(ADR-A-005: Gateway/Tool boundary are opaque dicts by design). The
simplest signal that works uniformly across FakeModelGateway and any
future real Gateway is "did it call a tool."

**Why should_complete and should_continue are separate methods instead of
one branch.** A future, smarter policy (the director's brief: "Policy
must be replaceable later") might want a turn to be neither complete nor
eligible to continue -- e.g. a turn that asked for a tool but also
signaled the task should pause for human review. Keeping the three checks
(`tool_failed`, `should_complete`, `should_continue`) as separate,
independently overridable static/class methods on `RuntimeDriver` means a
subclass can change one without having to reimplement `_run_loop`'s
control flow. Today, `should_continue` is the logical complement of
`should_complete` and `tool_failed` combined -- the `break` branch in
`_run_loop` exists to handle a future policy where that's no longer true,
not because it's reachable now.

**Why tool failure is a hard stop, not a retry.** The director's brief
lists "failed-tool path" as a required test, implying the driver must do
*something* deliberate on failure, but doesn't specify retry semantics.
Retrying is a real design decision (how many attempts? backoff? does the
model get to see the failure and try something else?) that belongs to a
future, explicitly-designed retry policy, not to a placeholder default.
Stopping cleanly with `STOPPED_TOOL_FAILURE` and the turns run so far is
the simplest safe behavior: nothing is retried, nothing is silently
swallowed, and the caller gets an accurate outcome plus everything needed
to inspect what happened (the failed Turn's `tool_calls` list, including
the failing observation).

**Why a driver-level `max_turns` distinct from engine.py's
`_MAX_TOOL_ROUNDS_PER_TURN`.** These bound different things.
`_MAX_TOOL_ROUNDS_PER_TURN` (engine.py, unchanged by this task) bounds
tool-call rounds *inside* a single `run_turn()` call and is a safety net
against a misbehaving fake/gateway within one turn. `DriverConfig.
max_turns` bounds how many *separate turns* the driver will run in one
`execute_task`/`execute_until_stop` call -- the actual "how much work
before we give up and report back" policy. The driver never reads or
modifies the engine's internal constant; it respects it only in the sense
that it doesn't need to duplicate that protection.

**Why checkpointing is periodic (`checkpoint_every`, default every turn)
plus guaranteed on completion.** The director's brief requires
"checkpoint + resume during execution" to actually work, which means a
checkpoint has to exist at whatever point execution stops -- whether that
stop is a clean completion, a tool failure, or hitting max_turns.
Checkpointing after every turn by default is the simplest way to
guarantee that without the driver having to special-case each of the
three stop paths; `checkpoint_every` exists so a future policy can trade
checkpoint frequency against overhead once that becomes a real concern
(it isn't yet, per the Bible's free/cheap-first cost objective --
checkpointing every turn against a local/free-tier Postgres has no
meaningful cost at this stage).

**Why RuntimeDriver never touches AgentRuntime's private attributes.**
The director's brief: "Driver must use existing AgentRuntime only."
`RuntimeDriver` calls only `create_task`, `start_agent_run`,
`start_session`, `run_turn`, `checkpoint`, `resume`, and `complete_task`
-- the exact seven primitives the brief lists as already existing.
Nothing in engine.py was modified for this task. Where the driver needs
the current Task object for a non-completed outcome, it deliberately
returns `task_id: str` instead of re-fetching via `resume()` (which would
emit a spurious `task.resumed` event just to peek at status) -- `task:
Task` on `DriverResult` is populated only on the `COMPLETED` outcome,
directly from `complete_task()`'s return value.

## Consequences

- The policy is intentionally not "smart": it cannot recognize a stuck
  loop where the model keeps calling the same tool without progress, and
  it cannot recognize a "final" response that happens not to be the exact
  turn where `tool_calls` is empty (e.g. a model that emits a completion
  message *and* an unnecessary tool call in the same turn would be read
  as "still working," not "done"). This is accepted as correct scope for
  A-005; a smarter policy is future work once a real Model Gateway
  exists to observe actual response shapes against (this mirrors ADR-A-006's
  reasoning for deferring loop-continuation policy in the first place).
- `RuntimeDriver` is a plain class, not itself behind a Protocol. A future
  swap-in policy can simply be a different class with the same four
  methods (`execute_task`, `execute_until_stop`, `should_continue`,
  `should_complete`) plus `tool_failed`; no interface was introduced
  speculatively ahead of a second implementation actually existing.

## Validation

Revisit this ADR once Claude B's real Model Gateway exists and its actual
response shapes (finish_reason, structured completion signals, etc.) can
be observed -- at that point `should_complete`/`should_continue` may gain
a second, real signal beyond "did it call a tool," and retry policy for
`tool_failed` can be designed against real tool-failure modes instead of
the single synthetic `status: "error"` convention used by tests today.

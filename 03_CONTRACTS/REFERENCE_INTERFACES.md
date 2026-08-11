# Reference Interfaces

**Status:** NORMATIVE FOR FIRST IMPLEMENTATION; exact syntax may vary.

These are behavioral interfaces, not mandatory language syntax.

## Model Gateway

```text
infer(request: ModelRequest) -> ModelResult | ModelError
```

Request must contain:
- task/session/turn identity;
- capability requirements;
- bounded context;
- tool definitions available for this turn;
- budget envelope;
- routing constraints.

Result must contain:
- normalized output;
- tool intents, if any;
- selected model/provider metadata;
- usage metadata when available;
- latency/timing metadata;
- correlation identifiers.

## Router

```text
select(requirements, candidates, budget, session_state) -> RouteDecision
```

A RouteDecision records:
- selected candidate;
- rejected candidates/reasons when useful;
- fallback chain;
- budget class;
- routing rationale;
- safe switch boundary.

## Permission Engine

```text
decide(capability, actor, resource, arguments, policy_context) -> allow|ask|deny
```

## Tool Runner

```text
execute(tool_request, permission_decision, sandbox_context) -> ToolResult
```

The runner must reject calls without an affirmative permission decision.

## Context Manager

```text
assemble(task, session, turn, memory, history, tools, budget) -> ContextBundle
```

The bundle must expose provenance and budget accounting where practical.

## Checkpoint Service

```text
create(execution_state) -> Checkpoint
restore(checkpoint_id) -> ExecutionState
```

## Event Store

```text
append(event) -> event_id
read(correlation/task/session filters) -> EventStream
```

Events are append-oriented and auditable.

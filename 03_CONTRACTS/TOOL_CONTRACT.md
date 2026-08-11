# Tool Contract

**Status:** FROZEN — architectural contract

## Purpose
Expose a bounded capability an agent may request.

## Responsibilities
- describe a capability;
- validate inputs;
- execute within the permitted boundary;
- return structured success/error information;
- expose timeout/cancellation behavior where supported.

## Non-responsibilities
- deciding whether the agent is authorized;
- choosing the model;
- storing arbitrary agent memory.

## Invariants
1. Tool existence does not grant permission.
2. External side effects are attributable to a task/session/agent.
3. Tool output must have practical size/time limits.

## Deferred
- exact tool protocol;
- tool schema language;
- timeout defaults;
- retry semantics.

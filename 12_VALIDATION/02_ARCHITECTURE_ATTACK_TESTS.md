# Architecture Attack Tests

The architecture must be attacked before implementation.

## A01 — Model disappearance

**Question:** What happens if the preferred model disappears?

Expected:
- route to another capability-equivalent model;
- preserve task/session state;
- record provider failure;
- no project rewrite.

## A02 — Provider API change

Expected:
- adapter/registry update;
- normalized core contract unchanged.

## A03 — Runtime death

Expected:
- restore from checkpoint/state;
- resume task.

## A04 — 100 MB tool output

Expected:
- output bound;
- truncation/summarization;
- thrashing detection.

## A05 — Agent loop

Expected:
- detect repeated state/action pattern;
- stop or escalate.

## A06 — Child-agent failure

Expected:
- parent survives;
- child result is classified;
- retry/reassignment possible.

## A07 — Secret request

Expected:
- permission engine denies;
- secret never enters ordinary model context.

## A08 — Azure reaches zero

Expected:
- workload migrates or shuts down cleanly;
- durable state remains.

## A09 — Database disappears

Expected:
- restore from backup;
- replay or reconcile events where applicable.

## A10 — Six-month resume

Expected:
- project/session can be reconstructed from durable state, artifacts and memory.

## A11 — Malicious README

Expected:
- instructions in README are treated as untrusted data;
- no privileged action is authorized solely because README asks for it.

## A12 — Malicious MCP server

Expected:
- server is isolated and permissioned;
- unexpected capability requests are denied/asked.

## A13 — Provider quota exhaustion

Expected:
- fallback route;
- quota event recorded;
- no silent infinite retry.

## A14 — Context thrashing

Expected:
- guard trips;
- context is compacted or task fails diagnostically.

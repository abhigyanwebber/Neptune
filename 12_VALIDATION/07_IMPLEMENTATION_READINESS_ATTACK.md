# Implementation Readiness Attack

Neptune must survive these tests before Phase 1 is declared implementation-ready.

## Supply failure

Remove Gemini.

Expected:
- routing selects another valid lane;
- state and task logic remain unchanged.

## Dual-home failure

Remove one provider hosting a dual-homed model.

Expected:
- another provider can serve the same capability/model identity when currently available.

## Free quota exhaustion

Exhaust the primary free lane.

Expected:
- queue, fallback, cheap overflow, or explicit escalation;
- no silent runaway spend.

## Temporary credit expiration

Set Azure/NIM/other credit balance to zero.

Expected:
- Neptune still operates in reduced $0 mode.

## Local failure

Remove the laptop's local model.

Expected:
- remote inference still works;
- only support functions degrade.

## Database provider failure

Remove the active database.

Expected:
- architecture can restore/replace the state provider without changing project logic.

## Free PaaS sleep

Suspend a free application service.

Expected:
- the system either tolerates cold start or routes that workload elsewhere.

## Provider catalog deletion

Delete a model from the registry.

Expected:
- router chooses a replacement capability candidate.

## Context pressure

Force a long tool-heavy session.

Expected:
- context compaction/trimming prevents unbounded growth;
- critical task state survives.

## Security attack

Provide a repository containing hostile instructions.

Expected:
- content is treated as data;
- tool permissions remain externally enforced;
- sandbox boundaries remain intact.

## Recovery attack

Kill the runtime during a task.

Expected:
- task/session can resume from durable state/checkpoint.

## Economic attack

Restrict the entire system to C0/C1 resources.

Expected:
- a useful reduced-capability Neptune remains operational.

## Upgrade attack

Allow C3/C4 resources temporarily.

Expected:
- stronger models/compute can be added without architectural changes.

Passing these attacks is more important than matching a particular provider stack.

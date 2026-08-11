# Implementation Readiness

**Purpose:** final Phase 0 gate.

Neptune is ready for implementation when the implementation agent can make concrete technology choices without inventing missing architectural boundaries.

## 1. The implementation agent must know

### Identity

The system is Neptune.

### Mission

Build reusable production-capable agent infrastructure using the strongest feasible free/cheap resource portfolio.

### Core architectural rule

```text
Project
  ↓
Neptune contract
  ↓
Adapter
  ↓
External resource
```

### Economic rule

```text
free durable
   >
free constrained
   >
temporary credit
   >
cheap paid
   >
expensive paid
```

unless practical reliability/operational cost justifies otherwise.

## 2. The implementation agent may choose

- language;
- framework;
- exact database implementation;
- exact sandbox technology;
- exact router scoring;
- exact context retrieval algorithm;
- exact deployment topology;
- exact provider SDK;
- exact schema normalization details.

Choices must satisfy the contracts and acceptance criteria.

## 3. The implementation agent must not silently change

- provider independence;
- state ownership;
- permission/sandbox separation;
- project memory isolation;
- event/audit requirements;
- checkpoint semantics;
- resource lifecycle semantics;
- $0 baseline viability;
- replaceability of external providers.

## 4. Reference implementation starting point

Start with the smallest vertical slice:

```text
Task
 → Session
 → Context
 → Model Gateway
 → LiteLLM
 → one free model
 → one safe tool
 → Event
 → Checkpoint
 → Verification
```

Then add:

```text
second model/provider
 → fallback
 → quota accounting
 → persistence
 → observability
 → sandbox hardening
 → deployment
```

Do not implement every registry candidate before validating the vertical slice.

## 5. Production readiness gates

### Gate A — Functional

The agent can complete bounded coding tasks.

### Gate B — Resilience

Primary provider failure does not destroy session state.

### Gate C — Economic

The system can operate on the durable free baseline.

### Gate D — Security

Untrusted repository content cannot silently gain privileges.

### Gate E — Recovery

A failed runtime can resume from durable state/checkpoint.

### Gate F — Operations

Usage, failures, provider health, and resource expiry are visible.

### Gate G — Replacement

A provider can be removed and replaced without rewriting agent logic.

## 6. Final question

If an implementation agent can answer:

> "What must I preserve, what may I choose, what resources should I try first, what happens when they fail, and what makes Neptune production-ready?"

without asking the architecture owner to invent missing fundamentals, Phase 0 is ready.

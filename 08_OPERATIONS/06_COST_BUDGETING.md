# Cost & Capacity Operations

## Objective

Maximize useful agent work per unit of practical cost.

## Capacity order

```text
C0 durable free
  ↓
C1 constrained free
  ↓
C2 temporary credit
  ↓
C3 cheap paid overflow
  ↓
C4 exceptional paid escalation
```

## Spend rules

### Rule 1 — free first

Use adequate free capacity before consuming paid or expiring capacity.

### Rule 2 — credits are ammunition

Use expiring credits for workloads that materially benefit from burst capacity.

### Rule 3 — don't waste credits on steady-state

A task that can run indefinitely on free infrastructure should not consume finite cloud credit merely for convenience.

### Rule 4 — buy tier jumps

If spending becomes necessary, prefer a small purchase that removes a real bottleneck rather than spreading money across many weak services.

### Rule 5 — keep a buffer

Do not consume the entire temporary balance.

Reserve capacity for:
- incidents;
- difficult tasks;
- migration;
- final deployment;
- benchmark validation.

## Accounting dimensions

Record per task/session:

- model/provider;
- input/output tokens;
- estimated financial cost;
- free quota consumed;
- temporary credit consumed;
- latency;
- retries;
- escalations.

## Budget envelopes

Future implementation should support:

```text
task budget
session budget
daily budget
provider budget
temporary-credit budget
```

The exact enforcement mechanism is implementation work.

## Decision threshold

A paid resource is justified when:

```text
reliability gain
+
capability gain
+
operational savings
>
financial cost
```

The equation is conceptual, not a literal runtime formula.

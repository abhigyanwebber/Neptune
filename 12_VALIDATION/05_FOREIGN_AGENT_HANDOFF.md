# Foreign-Agent Handoff Test

**Purpose:** Determine whether this repository communicates the architecture without forcing an implementation agent to invent the system boundaries.

## The agent should be able to answer

1. What is the infrastructure?
2. What is a project?
3. What is a Task?
4. What is an Agent?
5. What is a Session?
6. How does model access happen?
7. How do tools become executable?
8. Where are permissions enforced?
9. Where does sandboxing occur?
10. Who owns durable state?
11. What survives provider failure?
12. What survives runtime failure?
13. How are project memories isolated?
14. Which resources are temporary?
15. Which decisions are intentionally deferred?

## The agent should NOT be expected to know

- exact implementation language;
- exact database;
- exact routing equation;
- exact retrieval algorithm;
- final sandbox technology;
- final cloud topology.

Those are deliberate implementation choices.

## Pass condition

A competent implementation agent can produce a reasonable Phase 1 skeleton without changing any architectural boundary or asking what the system is supposed to mean.

## Fail condition

The agent must invent:

- the domain relationships;
- who owns state;
- whether models are provider-coupled;
- whether tools bypass permissions;
- whether Azure is foundational;
- whether project logic belongs in the core.

If it must invent those, Phase 0 is incomplete.


## Economic understanding test

The implementation agent must also understand:

1. The target is production-capable infrastructure under a free-or-cheap budget.
2. Free/student resources are valuable but replaceable.
3. Temporary credits are burst capital.
4. A $0 dependency is not automatically preferable if it creates unacceptable operational burden.
5. The implementation should preserve a $0 baseline where practical and permit cheap upgrades.
6. No single free provider may become an implicit architectural requirement.

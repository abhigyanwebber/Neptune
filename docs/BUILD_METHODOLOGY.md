# Neptune Build Methodology (Internal)

This document preserves the internal governance and build-methodology material that
previously lived in the root `README.md`. The README is now a concise, mentor-facing
landing page; this file holds the process detail that was moved out of it.

## Authority order

When documents disagree, use this order:

1. `01_BIBLE/` — architectural principles and boundaries
2. `02_ARCHITECTURE/` — canonical relationships and dependency direction
3. `05_DECISIONS/` — frozen architectural decisions
4. `03_CONTRACTS/` — component responsibilities and invariants
5. `09_SCHEMAS/` — machine-readable representations
6. `12_VALIDATION/` — acceptance and phase gates
7. `04_RESEARCH/` — evidence and recommendations
8. `06_REGISTRIES/` — volatile provider/resource facts

Research and registry facts may change. Architecture changes only through an explicit decision.

## The critical distinction

```text
ARCHITECTURE
    = what Neptune must remain

REFERENCE IMPLEMENTATION
    = how the first version will be built

RESOURCE REGISTRY
    = what external resources are currently available
```

Do not confuse them.

## Start here if you are implementing Neptune

Read in this order:

1. `00_SOURCE_MATERIALS/SOURCE_MANIFEST.md`
2. `01_BIBLE/00_DOCUMENT_CONTROL.md`
3. `01_BIBLE/01_VISION_AND_PRINCIPLES.md`
4. `02_ARCHITECTURE/01_SYSTEM_MAP.md`
5. `02_ARCHITECTURE/06_CORE_DOMAIN_MODEL.md`
6. `02_ARCHITECTURE/02_DEPENDENCY_DIRECTION.md`
7. `02_ARCHITECTURE/07_BOUNDARY_RULES.md`
8. `03_CONTRACTS/00_CONTRACT_CONVENTIONS.md`
9. relevant component contracts
10. `05_DECISIONS/00_ADR_INDEX.md`
11. `01_BIBLE/14_REFERENCE_PRODUCTION_BLUEPRINT.md`
12. `01_BIBLE/16_FINAL_IMPLEMENTATION_SPEC.md`
13. `02_ARCHITECTURE/11_REFERENCE_COMPONENT_GRAPH.md`
14. `02_ARCHITECTURE/12_REFERENCE_DATA_FLOW.md`
15. `02_ARCHITECTURE/13_REFERENCE_BUILD_ORDER.md`
16. `03_CONTRACTS/REFERENCE_INTERFACES.md`
17. `06_REGISTRIES/REFERENCE_STACK_REGISTRY.md`
18. `12_VALIDATION/08_FINAL_BIBLE_AUDIT.md`
19. `01_BIBLE/17_FINAL_FREEZE.md`
20. `12_VALIDATION/09_PHASE_1_ACCEPTANCE_GATES.md`

## First build

Do not build the whole platform at once.

Start with:

```text
Task
 -> Session
 -> Context
 -> Model Gateway
 -> Router
 -> LiteLLM
 -> one free model
 -> one safe tool
 -> Event
 -> Checkpoint
 -> Verification
```

Only after that passes should additional providers, advanced routing, context compaction,
stronger sandboxing, deployment automation, and multi-agent execution be added.

## Development methodology

Neptune is initially built by two Claude implementation accounts under a director layer.

- **Claude A:** Core / Control Plane
- **Claude B:** Infrastructure / Integration
- **Human operator + ChatGPT:** directors

Both accounts receive the same Bible and repository. The account is then explicitly
identified as A or B and follows the corresponding role.

This is a development methodology, not a Neptune runtime feature.

See `14_DEVELOPMENT_ORCHESTRATION/` for the full protocol (worker roles, account bootstrap,
work allocation, git integration protocol, director control, definition of done).

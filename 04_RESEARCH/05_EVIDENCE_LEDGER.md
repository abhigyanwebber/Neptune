# Evidence Ledger

This is the initial architecture evidence ledger.

| ID | Observation | Source | Architectural implication | Status |
|---|---|---|---|---|
| E-001 | Free provider catalogs change rapidly | R01 | Multi-provider registry and routing | FOUNDATION |
| E-002 | Harness and model are separable | R02 | Agent runtime is provider-independent | FOUNDATION |
| E-003 | Model differences can dominate hard-task performance | R02/R01 | Capability-based model selection | FOUNDATION |
| E-004 | Context management affects agent quality | R02 | Dedicated context engine | FOUNDATION |
| E-005 | Tool definitions can consume context | R02 | Deferred tool-definition loading | PROPOSED |
| E-006 | Oversized tool output can cause thrashing | R02 | Output bounds + thrashing guard | PROPOSED |
| E-007 | Sessions/checkpoints/Git serve different purposes | R02 | Separate execution and artifact state | FOUNDATION |
| E-008 | Child agents can isolate context | R02 | Parent/child agent architecture | PROPOSED |
| E-009 | Sandbox and permission can be separated | R02 | Capability + policy + approval + sandbox | FOUNDATION |
| E-010 | Prompt injection is systemic | R02 | Untrusted-input model and security boundary | FOUNDATION |
| E-011 | OpenHands has strong multi-agent substrate characteristics | R02 | Candidate runtime, not core dependency | CANDIDATE |
| E-012 | Aider is strong as an open model-agnostic foundation | R02 | Candidate harness/reference | CANDIDATE |
| E-013 | Free LLM supply has stable and bonus layers | R01 | Structural vs opportunistic provider lanes | PROPOSED |
| E-014 | Local laptop is constrained for primary large-model inference | R01 | Local support tier | FOUNDATION |
| E-015 | Multi-model switching can reduce cache warmth | R01 | Cache-aware routing | PROPOSED |
| E-016 | Student resources have activation/expiration differences | R03 | Claim-vs-activation lifecycle | FOUNDATION |
| E-017 | Azure credits are finite and quota-constrained | R03 | Burst capital + exit strategy | FOUNDATION |
| E-018 | Free services can sleep/suspend/cap bandwidth | R03 | Workload suitability classification | PROPOSED |
| E-019 | Student/startup programs have different eligibility paths | R03 | Separate resource classes | FOUNDATION |
| E-020 | Free backbone can support broad full-stack infrastructure | R03 | $0 baseline architecture | PROPOSED |

## Evidence status meanings

- FOUNDATION = stable architectural principle derived from research.
- PROPOSED = architecture response that still needs validation.
- CANDIDATE = external implementation candidate.
- SNAPSHOT = time-sensitive resource fact.

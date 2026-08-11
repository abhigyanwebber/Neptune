# 4. Architecture Overview

The system is divided into six logical layers.

``` text
L0 — RESOURCE LAYER
Cloud / compute / providers / storage / external services

L1 — INTELLIGENCE LAYER
Model registry / gateway / routing / quotas / fallback

L2 — AGENT LAYER
Agent lifecycle / orchestration / planning / delegation / recovery

L3 — EXECUTION LAYER
Tools / MCP / filesystem / shell / Git / browser / sandbox

L4 — STATE LAYER
Tasks / sessions / events / context / memory / checkpoints

L5 — OPERATIONS LAYER
Security / secrets / observability / CI/CD / backups / lifecycle
```

Future applications sit above the infrastructure:

``` text
                 FUTURE PROJECTS
          ┌──────────┼───────────┐
          ↓          ↓           ↓
        Argus    Workspace OS   Other
          └──────────┼───────────┘
                     ↓
             AGENT INFRASTRUCTURE
```

------------------------------------------------------------------------

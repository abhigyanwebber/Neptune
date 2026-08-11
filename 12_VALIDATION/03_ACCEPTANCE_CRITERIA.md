# Phase 0 Acceptance Criteria

The architecture is acceptable only if:

1. a project can consume the infrastructure without importing provider SDKs;
2. a model provider can be replaced without rewriting agent logic;
3. a runtime can be replaced without rewriting project logic;
4. agent state survives provider failure;
5. agent state survives runtime failure;
6. permissions cannot be bypassed by model instructions;
7. untrusted repositories can be isolated;
8. oversized tool output cannot consume the entire context;
9. temporary resources have exit paths;
10. provider/resource changes are represented in registries;
11. execution can be audited through events;
12. critical artifacts can be restored;
13. multi-agent work does not require multi-agent mode for simple tasks;
14. the cost/resource system can identify why a task consumed capacity;
15. architecture decisions have traceable research or explicit design rationale.


## Production/economic readiness additions

16. a useful reduced-capability mode operates without temporary credits;
17. model supply has at least one primary free lane and independent fallback capacity;
18. free/provider catalog changes do not require agent-logic rewrites;
19. model quotas are visible to routing/accounting;
20. temporary credits have explicit activation and exit records;
21. a concrete reference stack exists so implementation can begin without repeating the research;
22. provider/model facts remain registry data rather than core architectural constants.

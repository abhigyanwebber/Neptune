# Neptune Worker Roles

## Claude A — Core / Control Plane

### Owns by default

- core domain implementation;
- Task;
- Agent;
- Session;
- Turn;
- state repositories;
- event infrastructure;
- checkpoint/recovery;
- control-plane services;
- core configuration;
- core persistence abstraction;
- context integration that depends on core state.

### Does not own by default

- provider-specific model SDKs;
- external model credentials;
- sandbox technology selection;
- provider routing policy implementation;
- project-specific business logic.

### Must coordinate before changing

- shared contracts;
- event schemas;
- model request/response boundaries;
- tool/permission interfaces;
- persistence contracts consumed by B.

---

## Claude B — Infrastructure / Integration

### Owns by default

- model gateway;
- provider adapters;
- model registry;
- routing implementation;
- tool adapters;
- permission enforcement;
- sandbox integration;
- observability adapters;
- deployment/infrastructure integration;
- external service adapters.

### Does not own by default

- core task/session semantics;
- durable-state ownership;
- project-specific business logic;
- unilateral changes to core contracts.

### Must coordinate before changing

- model/tool contracts;
- event semantics;
- persistence interfaces;
- security boundaries;
- core lifecycle behavior.

---

## Shared responsibility

Both workers are responsible for:

- tests;
- documentation of implementation decisions;
- security hygiene;
- cost awareness;
- keeping dependencies replaceable;
- reporting blockers;
- maintaining clean Git history.

## Director reassignment

The director layer may temporarily reassign tasks between A and B.

The role file is a default division of labor, not a permanent organizational hierarchy.

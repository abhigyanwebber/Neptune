# 16. L5 --- Operations Layer

## 16.1 Secrets

The system should provide a centralized secret abstraction.

Conceptual interface:

``` text
get_secret()
request_secret()
scope_secret()
revoke_secret()
rotate_secret()
```

Agents should receive the minimum credential required for a specific
operation.

They should not receive the entire environment by default.

## 16.2 Observability

Observability must cover:

``` text
agents
tasks
model calls
tool calls
MCP calls
runtime
sandbox
database
routing
providers
CI/CD
deployments
errors
```

Potential initial services:

-   Sentry
-   New Relic

These are implementation resources, not permanent architectural
dependencies.

## 16.3 Usage Accounting

Every model call should eventually record:

``` text
provider
model
input tokens
output tokens
latency
estimated cost
quota impact
retry count
task
agent
session
```

This enables infrastructure economics analysis.

------------------------------------------------------------------------

# 17. CI/CD

GitHub Actions is the initial CI/CD backbone.

Standard pipeline:

``` text
push
 ↓
lint
 ↓
tests
 ↓
security checks
 ↓
build
 ↓
artifact
 ↓
deploy
```

Agent-created code should pass normal CI/CD gates.

Agents should not be given permission to silently bypass them.

------------------------------------------------------------------------

# 18. Deployment Architecture

## 18.1 Local Control Node

The user's laptop initially hosts:

-   development tools;
-   model gateway development;
-   local orchestration;
-   SQLite;
-   small local models;
-   infrastructure administration.

It is not the primary large-model inference server.

## 18.2 Persistent Free Compute

Oracle Always Free is a candidate for lightweight persistent
infrastructure.

## 18.3 Serverless

Cloudflare Workers is a candidate for lightweight edge/API functions.

## 18.4 Frontend

Vercel or Netlify are candidate free frontend layers.

## 18.5 Burst Compute

Azure and notebook GPU environments are temporary acceleration
resources.

They must not be required for the base system to function.

------------------------------------------------------------------------

# 59. Observability Architecture — Expanded

Observability should be event-driven.

Every important action should be attributable to:

```text
resource
provider
model
agent
task
session
runtime
tool
user
```

## 59.1 Metrics

### Model

- request count;
- tokens;
- latency;
- errors;
- cost;
- quota.

### Agent

- task completion;
- retries;
- tool calls;
- turns;
- escalations;
- failures.

### Runtime

- CPU;
- memory;
- execution duration;
- sandbox failures;
- process failures.

### Provider

- availability;
- latency;
- quota;
- catalog changes;
- failure rate.

---

# 60. Artifact and Audit Model

The infrastructure should preserve important artifacts:

```text
task specification
plan
context summary
tool results
code diff
tests
logs
checkpoint
final result
```

Sensitive data should be redacted according to policy.

Artifacts must be linked to task/session IDs.

---

# 61. Backup and Disaster Recovery

The infrastructure must define recovery classes.

### R0 — Disposable

Caches and temporary runtime state.

### R1 — Recoverable

Sessions and temporary artifacts.

### R2 — Important

Agent state, task records, memory, event logs.

### R3 — Critical

Infrastructure configuration, provider registry, secrets metadata, architectural specifications.

The actual secret values should not be stored in ordinary backups unless encrypted and explicitly intended.

---

## Economic operations

`08_OPERATIONS/06_COST_BUDGETING.md` defines the operational economic hierarchy. Neptune must remain useful in a C0/C1-only mode and treat temporary credits as burst capacity.


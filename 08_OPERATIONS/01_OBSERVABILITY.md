# Observability

## Event attribution

Important events should be attributable to:

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

## Model metrics

- requests
- input/output tokens
- latency
- errors
- cost
- quota

## Agent metrics

- completion
- retries
- turns
- tool calls
- escalations
- failures

## Runtime metrics

- CPU
- memory
- execution duration
- process failure
- sandbox failure

## Provider metrics

- availability
- latency
- quota
- catalog changes
- failure rate

## Required correlation IDs

At minimum:

```text
task_id
session_id
agent_id
runtime_id
event_id
provider_request_id
```

# Reference End-to-End Data Flow

## Normal turn

```text
1. Request arrives
2. Task is loaded/created
3. Session is loaded/created
4. Context Manager assembles bounded context
5. Model Gateway receives capability request
6. Router evaluates candidates
7. Provider adapter executes request through LiteLLM
8. Model returns text/tool intent
9. Permission Engine evaluates tool intent
10. Sandbox executes allowed tool
11. Tool output is bounded and normalized
12. Event is appended
13. Usage is recorded
14. Checkpoint is created at the configured boundary
15. Verification decides continue / retry / complete
```

## Provider failure

```text
provider error
 -> record failure
 -> cooldown candidate
 -> select fallback
 -> preserve same task/session identity
 -> continue from durable context
```

## Runtime failure

```text
runtime termination
 -> runtime failure event
 -> durable state remains
 -> locate latest checkpoint
 -> reconstruct session
 -> resume/retry
```

## Security failure

```text
untrusted content
 -> model sees content as data
 -> model requests tool
 -> permission policy decides independently
 -> sandbox enforces execution boundary
 -> denial is recorded
```

## Economic failure

```text
quota exhausted
 -> record usage
 -> candidate becomes unavailable
 -> fallback/queue/escalation
 -> enforce budget envelope
```

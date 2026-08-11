# Failure and Recovery

## Provider failure

```text
request
 ↓
provider fails
 ↓
classify failure
 ↓
retry if safe
 ↓
fallback route
 ↓
continue
```

## Runtime failure

```text
runtime dies
 ↓
checkpoint/state
 ↓
recreate runtime
 ↓
restore
 ↓
resume
```

## Context thrashing

```text
oversized tool output
 ↓
detect
 ↓
truncate/summarize
 ↓
retry if safe
 ↓
abort with diagnostic if repeated
```

## Resource expiry

```text
resource expiring
 ↓
find replacement
 ↓
migrate
 ↓
verify
 ↓
deactivate
```

## Critical invariant

A failed external resource should degrade capability, not erase durable state.

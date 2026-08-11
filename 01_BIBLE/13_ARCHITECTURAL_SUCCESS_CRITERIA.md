# Architectural Success Criteria

**Status:** FOUNDATION

The infrastructure succeeds when it can provide strong agentic capabilities without making expensive or temporary infrastructure a hidden prerequisite.

## Technical criteria

- provider-independent model access;
- controlled tool execution;
- recoverable task/session state;
- explicit security boundaries;
- observable execution;
- replaceable runtimes;
- project isolation;
- graceful degradation.

## Economic criteria

- meaningful $0 baseline;
- no single paid dependency required for the core architecture;
- temporary credits treated as accelerators;
- low-cost upgrade path;
- no unnecessary always-on infrastructure;
- resource lifecycle visibility.

## Production criteria

- failures are detectable;
- state can survive runtime/provider failure;
- external effects are controlled;
- resource expiration is visible;
- operator can understand what the system is doing;
- the architecture can scale up without changing its fundamental contracts.

## Anti-criteria

The architecture should be rejected or revised if:

- a free tier becomes an implicit hard dependency;
- one provider becomes irreplaceable;
- an expiring credit is required for normal operation;
- operational complexity overwhelms the value of a free component;
- security depends on model compliance;
- recovery depends solely on provider-side state.

## Phase boundary

These are evaluation criteria, not a requirement to implement all production machinery during Phase 0.

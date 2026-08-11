# ADR — Provider State Cannot Be Authoritative

**Status:** FOUNDATION

## Decision
Infrastructure state must be reconstructable without provider session state.

## Rationale
Provider changes and failures are expected.

## Consequences
May use provider caches as optimization.

## Validation
This decision must be revisited if the underlying research assumption changes materially.

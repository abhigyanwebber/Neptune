# ADR — Infrastructure Owns Durable Agent State

**Status:** FOUNDATION

## Decision
Providers/runtimes may not hold unrecoverable state.

## Rationale
Model switching and runtime failure must be survivable.

## Consequences
Requires durable state model.

## Validation
This decision must be revisited if the underlying research assumption changes materially.

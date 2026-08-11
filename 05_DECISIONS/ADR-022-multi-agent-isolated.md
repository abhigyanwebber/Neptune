# ADR — Child Agents Are Isolated

**Status:** PROPOSED

## Decision
Child agents receive bounded context, tools and permissions.

## Rationale
Prevents parent-context flooding and cross-agent interference.

## Consequences
Shared-state protocol required.

## Validation
This decision must be revisited if the underlying research assumption changes materially.

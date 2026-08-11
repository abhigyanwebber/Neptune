# ADR — Project-Agnostic Core

**Status:** FOUNDATION

## Decision
Projects consume infrastructure; they do not define core infrastructure.

## Rationale
Reusable infrastructure must survive across Argus, Workspace OS and future projects.

## Consequences
Project-specific logic belongs above the core.

## Validation
This decision must be revisited if the underlying research assumption changes materially.

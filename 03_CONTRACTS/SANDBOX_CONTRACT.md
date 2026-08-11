# Sandbox Contract

**Status:** PROPOSED — architectural boundary

## Purpose
Provide an execution boundary for agent actions.

## Responsibilities
- isolate declared runtime capabilities;
- constrain filesystem/process/network access as configured;
- expose lifecycle and failure state;
- support disposable execution where required.

## Non-responsibilities
- deciding business authorization;
- model selection;
- task planning.

## Invariants
1. Untrusted execution should not require unrestricted host access.
2. Sandbox capability does not imply permission.
3. Sandbox implementation is replaceable behind the boundary.

## Deferred
- Docker vs VM vs OS sandbox;
- network policy implementation;
- resource limits;
- escape detection.

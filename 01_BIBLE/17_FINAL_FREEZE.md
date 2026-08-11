# Neptune Bible Final Freeze

**Status:** FROZEN

## What is frozen

The following are frozen as Neptune's architectural intent:

- mission and production/economic objective;
- project-agnostic core;
- provider/resource replaceability;
- dependency direction;
- core domain meanings;
- durable-state ownership;
- project isolation;
- context/memory distinction;
- event/checkpoint semantics;
- tool/capability boundary;
- permission/sandbox separation;
- security enforcement outside model instructions;
- resource lifecycle semantics;
- temporary-credit/burst-capital rule;
- $0 baseline requirement;
- implementation handoff criteria;
- two-account development methodology for the initial build.

## What is not frozen

Concrete implementation technology remains provisional.

The implementation agent may replace:

- language;
- framework;
- database;
- model gateway;
- provider;
- runtime;
- sandbox implementation;
- observability stack;
- deployment target;
- storage technology.

A replacement must preserve the frozen architecture and satisfy the production/free-cheap objective.

## Change rule after freeze

Do not edit the Bible merely because implementation becomes inconvenient.

If implementation reveals a genuine architectural contradiction:

1. document the contradiction;
2. identify affected contracts;
3. propose alternatives;
4. evaluate production and economic impact;
5. make an explicit ADR;
6. update the affected authoritative document;
7. increment the Bible version.

## Normal implementation discoveries

Implementation details do not reopen the Bible.

Examples:

- different library;
- different ORM;
- different provider adapter;
- different container configuration;
- different query;
- different router scoring formula.

These belong in implementation decisions and development state.

## Final principle

> **Freeze the architecture. Keep the implementation adaptable.**

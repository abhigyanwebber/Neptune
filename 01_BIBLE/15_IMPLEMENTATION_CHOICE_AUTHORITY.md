# Implementation Choice Authority

**Status:** FROZEN ARCHITECTURAL RULE

## Purpose

Clarify who owns final implementation technology choices.

## Rule

Neptune's Bible defines the architecture and constraints.

The implementation agent is responsible for selecting the concrete technologies used to realize that architecture, subject to those constraints.

The Bible may provide:

- researched candidate technologies;
- a reference stack;
- known free/cheap resources;
- reasons a candidate appears suitable;
- compatibility constraints;
- cost constraints;
- fallback candidates.

Those are **recommendations and starting points**, not mandatory technology decisions, unless a separate ADR explicitly marks a choice as architecturally required.

## What the implementation agent must optimize

The chosen implementation should maximize:

1. production feasibility;
2. reliability;
3. security;
4. maintainability;
5. compatibility with Neptune's contracts;
6. free/cheap operational feasibility;
7. replaceability;
8. long-term sustainability.

## What the implementation agent may change

The agent may replace a proposed technology if it can demonstrate that the alternative better satisfies Neptune's constraints.

Examples:

- replace the proposed database;
- replace the proposed runtime;
- replace a model gateway;
- replace an observability backend;
- replace a hosting provider;
- replace a sandbox implementation.

## What the implementation agent may not change

Technology may not be changed in a way that violates:

- provider independence;
- durable-state ownership;
- project isolation;
- permission/sandbox separation;
- security boundaries;
- resource replaceability;
- the free/cheap production objective;
- the canonical domain model;
- frozen architectural contracts.

## Required decision record

When the implementation agent chooses a technology that differs materially from the candidate reference stack, it should record:

- chosen technology;
- rejected candidate;
- reason;
- cost implications;
- operational implications;
- replacement path.

This may be an implementation decision or ADR depending on whether the choice affects architecture.

## Important distinction

> **The Bible decides what Neptune must be. The implementation agent decides how to build it.**

That is intentional. The Bible must constrain implementation without micromanaging it.

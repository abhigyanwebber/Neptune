# Workspace OS Integration Boundary

Workspace OS is a consumer/application of the reusable infrastructure.

## Infrastructure responsibilities

- agent runtime;
- model gateway/routing;
- tool execution;
- permissions;
- state/session;
- memory/context;
- observability;
- deployment/resource abstractions.

## Workspace OS responsibilities

- SaaS product behavior;
- workspace UI;
- workspace types;
- user-facing billing/product logic;
- project-specific integrations;
- application-specific data models.

The SaaS product should consume infrastructure APIs rather than fork the core architecture.

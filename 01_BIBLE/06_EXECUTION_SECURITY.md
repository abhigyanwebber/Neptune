# 8. L3 --- Execution Layer

## 8.1 Capability Model

Agents may eventually access:

-   filesystem
-   shell
-   Git
-   browser
-   web
-   MCP servers
-   APIs
-   databases
-   package managers
-   build systems
-   testing systems
-   deployment systems

These are **capabilities**.

Capability does not imply permission.

## 8.2 Execution Boundary

The intended flow is:

``` text
Agent
  ↓
Permission Policy
  ↓
Sandbox
  ↓
Tool
  ↓
External Effect
```

Not:

``` text
Agent → unrestricted host execution
```

## 8.3 MCP

MCP is treated as a major extension mechanism.

It allows external capabilities to be added without modifying the agent
core.

Examples:

``` text
MCP
├── GitHub
├── browser
├── filesystem
├── database
├── cloud
└── future services
```

MCP servers remain external components.

The infrastructure owns their lifecycle, permission integration,
configuration, and observability where appropriate.

------------------------------------------------------------------------

# 9. Permission and Policy Model

## 9.1 Principle

**Capability and authorization must be separate.**

An agent may know that a tool exists without being allowed to execute
it.

## 9.2 Policy Hierarchy

Proposed precedence:

``` text
DENY
  >
ASK
  >
ALLOW
```

Policies may exist at:

-   global
-   workspace
-   agent
-   task
-   tool
-   operation

## 9.3 Sensitive Capabilities

The following require stronger controls:

-   deleting files;
-   modifying production infrastructure;
-   database migrations;
-   secret access;
-   credential management;
-   external publishing;
-   financial actions;
-   destructive cloud operations;
-   remote Git operations.

## 9.4 Structural Enforcement

Where possible, permissions should be enforced by:

-   OS sandbox;
-   container boundary;
-   filesystem boundary;
-   network policy;
-   credential scoping;
-   tool-level policy.

Prompt instructions alone are not considered a sufficient security
boundary.

------------------------------------------------------------------------

# 10. Sandbox Layer

## 10.1 Purpose

The sandbox isolates agent execution from the host.

Potential implementation:

``` text
Host
  ↓
Container
  ↓
Agent runtime
  ↓
Worktree
```

The sandbox should eventually support:

-   filesystem isolation;
-   process isolation;
-   controlled network access;
-   resource limits;
-   disposable environments;
-   reproducible environments.

## 10.2 Trust Levels

Proposed:

### Level 0 --- Read-only

Agent can inspect but cannot mutate.

### Level 1 --- Workspace

Agent can modify an assigned workspace.

### Level 2 --- Sandbox

Agent can execute code in an isolated environment.

### Level 3 --- External

Agent can interact with external systems under explicit policy.

### Level 4 --- High Risk

Sensitive or production actions requiring explicit approval.

------------------------------------------------------------------------

# 21. Security Principles

## S1 --- Least Privilege

Give agents only the permissions required.

## S2 --- Sandbox First

Untrusted execution should happen inside isolation.

## S3 --- Credential Minimization

Expose only necessary secrets.

## S4 --- Auditability

Important actions should be observable.

## S5 --- Reversibility

Destructive operations should have rollback/checkpoint mechanisms
whenever practical.

## S6 --- Explicit Escalation

High-risk capabilities require stronger approval.

## S7 --- No Trust in Model Intent

The model is not a security boundary.

A capable model can still:

-   misunderstand;
-   hallucinate;
-   follow malicious instructions;
-   process prompt injection;
-   make destructive mistakes.

------------------------------------------------------------------------

# 22. Prompt Injection and Tool Security

The infrastructure must assume that external content can contain
malicious instructions.

Potential attack surfaces:

``` text
web pages
GitHub issues
README files
documents
emails
MCP responses
API responses
repository code
tool output
```

External content must therefore be treated as **data**, not trusted
instructions.

The exact implementation is deferred to the security design phase.

------------------------------------------------------------------------

# 42. Permission Architecture — Expanded

The reports identify four broad permission architectures:

1. harness-enforced ask/allow/deny;
2. separated sandbox capability + approval policy;
3. mode-based tool groups;
4. approval-first toggle systems.

The infrastructure adopts the strongest conceptual combination:

```text
CAPABILITY
     +
SANDBOX
     +
POLICY
     +
APPROVAL
```

## 42.1 Capability

What the runtime is technically capable of doing.

## 42.2 Policy

What the agent is permitted to request.

## 42.3 Approval

Whether a human or higher-level policy must authorize a particular operation.

## 42.4 Sandbox

Where the operation is allowed to execute.

These are distinct.

---

# 43. Policy Precedence

Proposed precedence:

```text
GLOBAL DENY
     >
WORKSPACE DENY
     >
TASK DENY
     >
EXPLICIT APPROVAL
     >
ALLOW RULE
```

A deny rule should be able to prevent a capability from even being presented to the model when practical.

## 43.1 Policy Examples

```text
read repository       → allow
edit workspace        → allow
run tests             → allow
install package       → ask
network access        → ask
push Git branch       → ask
delete remote branch  → deny/strong approval
production migration  → deny/strong approval
secret export         → deny
```

These are examples, not frozen defaults.

---

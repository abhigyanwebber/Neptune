# 0. Document Control

## 0.1 Purpose

This document defines the architecture, boundaries, principles,
contracts, and roadmap for a reusable agentic AI infrastructure stack.

The infrastructure is intentionally **project-agnostic**. Projects
consume the infrastructure; they do not define it.

The core objective is to build a durable system around replaceable
external resources:

-   model providers
-   cloud providers
-   databases
-   agent runtimes
-   tools
-   compute
-   deployment platforms

The architecture should survive the replacement or disappearance of any
individual provider.

## 0.2 Source Basis

This first draft is derived primarily from the research reports already
produced for this infrastructure effort:

1.  **Research Brief 02 --- Free / Low-Cost LLM Infrastructure for
    Agentic Coding**
2.  **Claude Code Alternatives and the Agentic Coding Harness
    Landscape**
3.  **Student Developer Benefits & Free Infrastructure Research Report**

The reports establish several important conclusions:

-   a single free-model endpoint is not a reliable architectural
    dependency;
-   a router-fronted, multi-provider model supply chain is preferred;
-   the agent harness is at least as strategically important as the
    model supply;
-   context management, tool reliability, routing, permissions,
    sandboxing, and recovery are first-class concerns;
-   free/student infrastructure is useful but must be separated into
    durable backbone resources and expiring credits;
-   the user's laptop is a support/control node rather than a primary
    large-model inference server;
-   open agent substrates such as OpenHands are useful candidates for
    multi-agent execution;
-   Git, checkpoints, event streams, MCP, and sandboxing provide
    important building blocks.

Where this document introduces a design decision that was not explicitly
established by the reports, it is marked as a **Design Decision** or
**Proposed** rather than presented as a research finding.

## 0.3 Status Vocabulary

-   **FOUNDATION** --- architectural rule that should be treated as
    stable.
-   **DECISION** --- deliberate design choice.
-   **PROPOSED** --- current design, subject to validation.
-   **EXPERIMENTAL** --- must be tested before becoming infrastructure.
-   **EXTERNAL** --- supplied by an outside service/project.
-   **DEFERRED** --- intentionally not being built yet.

------------------------------------------------------------------------


## v0.5 naming

The reusable infrastructure is formally named **Neptune**. All future architectural documents should use Neptune as the system name.

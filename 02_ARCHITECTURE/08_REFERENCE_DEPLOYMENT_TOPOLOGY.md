# Reference Deployment Topology

**Status:** Reference architecture, not an irreversible deployment decision.

## Baseline topology

```text
                    INTERNET
                       |
              +--------+---------+
              |                  |
          Model APIs         External services
              |                  |
              +--------+---------+
                       |
                [Neptune Gateway]
                       |
                 [Agent Runtime]
                       |
              +--------+--------+
              |                 |
        [State/Data]       [Execution]
              |                 |
        PostgreSQL/Redis   Sandbox/MCP/Tools
              |
        [Observability]
              |
        Sentry / New Relic
```

## Control node

The user's Windows laptop is a development/control node.

It can host:

- Neptune source;
- local LiteLLM;
- SQLite;
- local support models;
- administration tools;
- development MCP servers.

It should not be assumed to provide production-grade uptime.

## Persistent free node

Oracle Always Free is a candidate for lightweight persistent components where its terms and availability are appropriate.

## Edge

Cloudflare Workers is a candidate for stateless functions, API edge logic, or lightweight gateways.

## Managed data

Supabase, Neon, and MongoDB Atlas are candidate data services.

The actual database selection depends on data shape and operational requirements.

## Burst

Azure student credits and notebook GPU resources are candidates for:

- temporary compute;
- deployment sprints;
- model experiments;
- batch jobs;
- GPU workloads.

## Deployment principle

Keep the control plane portable.

A provider outage should remove a resource, not remove Neptune.

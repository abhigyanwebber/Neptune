# Cross-Report Synthesis

Neptune is grounded in three supplied Manus reports:

1. Claude Code Alternatives and the Agentic Coding Harness Landscape
2. Research Brief 02 — Free / Low-Cost LLM Infrastructure for Agentic Coding
3. Student Developer Benefits & Free Infrastructure Research Report

## 1. What each report contributes

```text
Harness report
    ↓
agent-loop, tools, context, memory, permissions, sandbox,
recovery, multi-agent patterns

LLM report
    ↓
model supply, routing, quota engineering, model specialization,
free/cheap lanes, dual-homing, escalation

Student infrastructure report
    ↓
compute, storage, CI/CD, domains, secrets, monitoring,
authentication, databases, PaaS, GPU bursts, expiring credits
```

Neptune integrates these layers rather than treating them as separate projects.

## 2. Convergent architectural conclusions

### Provider volatility

The LLM report records multiple free-tier/model catalog failures and therefore recommends a router-fronted, multi-provider, capability-pinned supply chain.

Neptune response:

```text
Agent → Model Gateway → Router → Provider adapters
```

### Harness over API wrapper

The harness report shows that useful coding agents depend on context management, tools, permissions, recovery, repository understanding and execution discipline.

Neptune response:

```text
Agent Runtime
+ Context
+ Tools
+ State
+ Recovery
+ Verification
```

### Context is economics

The LLM report shows that agentic sessions are input-heavy and that context trimming/compaction, tool-output pruning and focused sessions materially reduce cost and quota consumption.

Neptune response:

Context management is both a capability subsystem and an economic control.

### State ownership

Harnesses differ in their use of sessions, checkpoints, Git, event streams and memory.

Neptune response:

The infrastructure owns recoverable state; providers are never the sole source of truth.

### Security

The harness report documents prompt-injection and dangerous-agent incidents.

Neptune response:

```text
capability
+
policy
+
approval
+
sandbox
```

must remain separate controls.

### Free infrastructure

The student report shows that a production-capable $0 backbone is possible but constrained by sleeping services, quotas, egress and lack of persistent GPU capacity.

Neptune response:

Use a durable free backbone, accept constrained services where appropriate, and reserve credits for high-value bursts.

## 3. Concrete reference strategy

```text
                 NEPTUNE
                    |
              Agent Runtime
                    |
             Context Manager
                    |
              Model Gateway
                    |
                 LiteLLM
                    |
          Capability / Quota Router
                    |
     +--------------+----------------+
     |              |                |
  Free lanes     Cheap lane      Escalation
     |              |                |
 Gemini/Groq/    Qwen/DeepSeek/   strongest
 Cerebras/       Mistral-class    available
 Mistral/etc.
     |
 local support
```

Surrounding services:

```text
GitHub + Actions
Oracle/Cloudflare
Supabase/Neon/MongoDB
Sentry/New Relic
Doppler/GitHub secrets
Azure/Kaggle/Colab/NIM as bursts
```

## 4. Research-derived failure lessons

The reports establish that:

- free model catalogs change;
- quotas can be the real bottleneck;
- provider availability can change mid-project;
- model switching can lose cache warmth;
- small models degrade on long-horizon planning;
- free infrastructure sleeps or caps usage;
- temporary credits expire;
- security failures can arise from prompts, MCP, plugins, lifecycle scripts and agent permissions.

Neptune is designed around these failures rather than assuming ideal conditions.

## 5. What remains intentionally implementation-defined

The reports do not establish:

- exact programming language;
- exact database;
- exact router formula;
- exact context retrieval/ranking algorithm;
- exact sandbox;
- exact deployment region;
- exact provider/model version at implementation time.

Those must be chosen during implementation and current resource verification.

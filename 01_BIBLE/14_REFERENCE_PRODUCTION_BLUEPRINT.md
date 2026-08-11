# Neptune Reference Production Blueprint

**Status:** REFERENCE BASELINE — implementation may begin from this blueprint  
**Authority:** derived from the three supplied research reports; implementation choices remain replaceable through the existing contracts.

## 1. Objective

Neptune is a reusable agent infrastructure designed to deliver production-capable agent execution while operating primarily on free or very low-cost resources.

The blueprint is intentionally concrete enough for implementation while preserving provider substitution.

## 2. Reference baseline

```text
PROJECT
  |
  v
AGENT RUNTIME / HARNESS
  |
  +--> CONTEXT + MEMORY
  |
  +--> MODEL GATEWAY
          |
          v
      LITELLM PROXY
          |
          +--> FREE PRIMARY
          |      Gemini free lane
          |
          +--> FREE SECONDARY / DUAL-HOME
          |      Groq
          |      Cerebras
          |      Mistral
          |
          +--> FREE HEAVY / BONUS
          |      Cloudflare Workers AI
          |      NVIDIA NIM credits
          |      OpenRouter :free
          |
          +--> CHEAP OVERFLOW
          |      Qwen / DeepSeek / Mistral-class paid APIs
          |
          +--> LOCAL SUPPORT
                 small coding / classification /
                 summarization models
```

The harness must speak to Neptune's model gateway, not directly to individual model providers.

## 3. Durable infrastructure backbone

The reference economic backbone is:

```text
GitHub + GitHub Actions
        |
        +-- source / CI
        |
        +-- configuration and release artifacts

Oracle Always Free
        |
        +-- lightweight persistent services where practical

Cloudflare Workers
        |
        +-- stateless edge/API functions where practical

Supabase / Neon / MongoDB Atlas
        |
        +-- durable data candidates, selected by workload

Sentry + New Relic
        |
        +-- error monitoring + observability

Doppler / GitHub secrets / student secret-management benefits
        |
        +-- secret delivery
```

No single item above is a permanent architectural dependency. The contracts define the dependency.

## 4. Temporary/burst resources

```text
Azure student credits
Kaggle GPU
Google Colab GPU
NVIDIA NIM credits
GCP education/startup credits if legitimately available
other verified promotional credits
```

These are acceleration resources.

They are not required for the $0 baseline.

The research specifically recommends using expiring cloud credits for short, high-value bursts while keeping the durable backbone outside them.

## 5. Application-facing services

When a consuming project needs them, the following can be attached:

```text
Frontend       -> Vercel Hobby / Netlify
Edge/API       -> Cloudflare Workers
Auth/billing   -> Clerk student benefit + Stripe
Database       -> Supabase / Neon / MongoDB Atlas
Secrets        -> Doppler / GitHub secrets
Monitoring     -> Sentry / New Relic
Scraping       -> Zyte Scrapy Cloud + scheduled jobs
```

These are **project-service candidates**, not mandatory Neptune components.

## 6. Model supply lanes

### Lane A — primary free reasoning/general

Gemini free tier.

Use for sustained planning/reasoning and research workloads where the current verified quota is adequate.

### Lane B — dual-homed fast work

Prefer a model identity that can be served by more than one provider, especially GPT-OSS-class open models on Groq/Cerebras/NVIDIA where current availability permits.

Purpose:

- cheap coding;
- tool calls;
- extraction;
- bounded agent work;
- resilience to provider/model catalog changes.

### Lane C — coding-specialist

Qwen-Coder / Qwen coding family or GLM-class coding models where current access and cost are acceptable.

Purpose:

- patch generation;
- diffs;
- code generation;
- debugging.

### Lane D — cheap overflow

Cheap paid Qwen/DeepSeek/Mistral-class models.

Use only when free lanes are insufficient.

### Lane E — escalation

Frontier or strongest available model through legitimate trials, credits, or deliberate small paid bursts.

Use for:

- architectural deadlocks;
- difficult debugging;
- large refactors;
- high-value reasoning;
- failure recovery.

### Lane F — local support

Small local models on the user's laptop.

Use for:

- classification;
- summarization;
- context compression;
- offline support;
- lightweight preprocessing.

The research explicitly found the laptop unsuitable as the primary inference tier but useful as a support tier.

## 7. Routing policy

Neptune's router should prefer:

1. capability fit;
2. free/durable capacity;
3. remaining quota;
4. health;
5. latency;
6. cost;
7. escalation only when necessary.

The exact scoring formula remains implementation work.

Routing must support:

- capability tags;
- provider health;
- quota awareness;
- fallback chains;
- cooldown;
- queueing;
- budget envelopes;
- model stickiness within a session when useful;
- safe switching at turn/compaction boundaries.

## 8. Context economics

Because agent sessions resend large amounts of context, context management is part of cost management.

Neptune should therefore:

- trim redundant tool output;
- compact completed work;
- preserve critical state;
- defer large tool definitions where practical;
- use repository maps/search rather than dumping repositories;
- avoid unnecessary retries with inflated context;
- switch model providers at safe boundaries rather than mid-generation.

## 9. Reference execution path

```text
Task
  ↓
Agent Runtime
  ↓
Context Manager
  ↓
Model Gateway
  ↓
LiteLLM
  ↓
Capability/Quota/Health Router
  ↓
Selected Model Provider
  ↓
Model decision
  ↓
Permission Engine
  ↓
Sandbox
  ↓
Tool / MCP
  ↓
External effect
  ↓
Observation
  ↓
Event Store + State
  ↓
Verification
  ↓
Checkpoint
  ↓
Next turn / completion
```

## 10. Reference production posture

The baseline should support:

- local development;
- persistent lightweight services;
- external model inference;
- provider failover;
- durable state;
- CI/CD;
- observability;
- secrets;
- controlled tool execution;
- recovery.

It does not require an always-on large GPU.

The research explicitly found that free infrastructure cannot sustainably host large production models; external inference and burst compute are therefore part of the intended design.

## 11. What is deliberately not part of the baseline

- permanent dependence on Azure;
- permanent dependence on OpenRouter;
- permanent dependence on any single free model;
- mandatory SaaS subscriptions;
- self-hosting a frontier model;
- a custom model-training platform;
- a custom Git platform;
- a custom auth/billing platform;
- a bespoke multi-agent development-management system.

These may be attached later only when a real requirement appears.

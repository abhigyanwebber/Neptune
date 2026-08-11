# 6. L1 --- Intelligence Layer

## 6.1 Purpose

The intelligence layer abstracts all model inference from the rest of
the system.

The agent should communicate with a model abstraction, not directly with
a provider.

``` text
Agent
  ↓
Model Gateway
  ↓
Router
  ↓
Provider
  ↓
Model
```

## 6.2 Model Gateway

**FOUNDATION**

The gateway is the single logical entry point for model inference.

Responsibilities:

-   normalize model requests;
-   resolve capability requirements;
-   route requests;
-   apply quotas;
-   handle retries;
-   perform provider failover;
-   collect usage telemetry;
-   expose consistent interfaces to agents.

The initial implementation is expected to use **LiteLLM** as an external
gateway component.

This is an implementation choice, not an architectural dependency.

## 6.3 Model Registry

**PROPOSED**

A registry describing available models by capability rather than by
brand.

Example:

``` yaml
capability: fast_general
models:
  - provider_a/model_x
  - provider_b/model_y
```

Potential capability classes:

-   fast_general
-   coding
-   reasoning
-   planning
-   summarization
-   classification
-   tool_use
-   vision
-   embedding
-   frontier_escalation

The registry must record:

-   model identifier
-   provider
-   capabilities
-   context limits
-   structured-output support
-   tool-calling support
-   availability
-   cost class
-   quota
-   health
-   preferred use cases

## 6.4 Routing

**FOUNDATION**

Routing should consider:

``` text
task type
+
capability
+
provider health
+
quota
+
latency
+
cost
+
failure history
```

The router should prefer the cheapest adequate model.

It should not use a frontier model merely because one is available.

## 6.5 Escalation

Hard tasks may escalate from:

``` text
free → cheap → strong → frontier
```

Escalation should be deliberate.

Examples:

-   difficult architectural decisions;
-   long-horizon planning;
-   repeated failure;
-   stuck-turn recovery;
-   high-risk code changes;
-   complex debugging.

## 6.6 Model Switching Rule

**FOUNDATION**

Do not switch providers unnecessarily during an active reasoning chain.

Model switching should preferably happen at:

-   task boundaries;
-   checkpoints;
-   context-compaction boundaries;
-   explicit escalation points.

This prevents context and reasoning continuity from being unnecessarily
damaged.

------------------------------------------------------------------------

# 46. Model Supply Architecture — Expanded

## 46.1 Provider Volatility

The model research documents repeated provider/model changes:

- free catalogs disappearing;
- model delistings;
- free tiers ending;
- quotas changing;
- providers changing catalog composition without long migration windows.

Therefore:

**Model availability is runtime data, not static architecture.**

## 46.2 Capability Pinning

Do not pin the infrastructure to:

```text
provider = X
model = Y
```

as the only definition.

Instead pin to:

```text
capability = coding
quality >= threshold
context >= threshold
tool_use = required
cost <= budget
```

Then resolve to current providers.

## 46.3 Dual-Homing

Where feasible, important model lanes should have multiple provider implementations.

Example:

```text
coding capability
    │
    ├── Provider A / Model X
    └── Provider B / Model X
```

Dual-homing the same model family is especially valuable because provider failure does not necessarily change model behavior.

## 46.4 Provider Reliability Record

Provider health should track:

- uptime;
- latency;
- rate-limit frequency;
- catalog stability;
- error rate;
- historical failures;
- quota remaining.

The provider with the best model is not automatically the provider with the best operational value.

---

# 47. Model Routing — Expanded

## 47.1 Routing Inputs

The router may use:

```text
task class
model capability
context requirement
tool-calling requirement
provider health
remaining quota
estimated cost
latency
failure history
current session model
cache state
escalation state
```

## 47.2 Routing Outputs

The router should return:

```text
selected provider
selected model
reason
expected capability
fallback chain
quota impact
cost class
```

## 47.3 Routing Lanes

Initial conceptual lanes:

```text
LOCAL SUPPORT
FREE PRIMARY
FREE SECONDARY
CHEAP OVERFLOW
STRONG ESCALATION
FRONTIER BURST
```

The exact models are maintained outside the core architecture in a provider registry.

---

# 48. Model Specialization

Research supports role specialization for cost efficiency.

Potential roles:

| Role | Desired property |
|---|---|
| Router | fast + structured |
| Classifier | cheap + reliable |
| Context compressor | cheap + stable |
| Extraction worker | cheap + high throughput |
| Coder | strong coding ability |
| Planner | strong reasoning |
| Reviewer | independent verification |
| Debugger | strong diagnosis |
| Escalation model | maximum available quality |

A model should be selected for the role it performs, not merely because it is the strongest available model.

---

# 49. Model Switching and State Ownership

A crucial rule from the LLM research:

> No external model provider should hold state that the agent infrastructure cannot reconstruct.

The infrastructure therefore owns:

- conversation state;
- task state;
- memory;
- checkpoints;
- summaries;
- tool history;
- provider metadata.

Provider-side state may be used for optimization, but must not be a single point of recovery.

## 49.1 Safe Switching Points

Prefer:

```text
turn boundary
checkpoint
compaction boundary
task boundary
explicit escalation
```

Avoid switching providers in the middle of an active generation.

---

# 50. Cache Architecture

Prompt caching creates a real tradeoff.

A single model/provider can benefit from stable prefixes.

Multi-provider routing can destroy cache warmth.

Therefore the router must consider:

```text
expected quality
+
cost
+
quota
+
health
+
cache value
```

A slightly cheaper provider is not necessarily better if switching causes a large cache penalty.

---

# 51. Local Model Strategy

The research concludes that the current laptop is not suitable as the primary large-model coding server.

The local tier is therefore optimized for:

- routing;
- classification;
- summarization;
- context compression;
- offline fallback;
- lightweight embeddings where practical;
- infrastructure administration.

Local models should not be selected because they are impressive on a benchmark alone.

They must be evaluated on:

- latency;
- RAM usage;
- structured output;
- reliability;
- useful accuracy;
- integration cost.

---

## Reference intelligence supply

Neptune's reference supply strategy is defined in `02_ARCHITECTURE/09_MODEL_SUPPLY_TOPOLOGY.md` and `06_REGISTRIES/MODEL_SUPPLY_CATALOG.md`. The harness should speak only to the model gateway; free/cheap providers are replaceable supply nodes.


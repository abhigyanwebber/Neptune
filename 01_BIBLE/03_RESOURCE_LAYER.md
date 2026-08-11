# 5. L0 --- Resource Layer

The resource layer contains external resources that the infrastructure
consumes.

## 5.1 Resource Categories

### Compute

-   local laptop
-   free cloud CPU
-   temporary cloud CPU
-   GPU notebook environments
-   burst GPU/cloud resources

### Model Providers

-   free providers
-   cheap providers
-   frontier providers
-   local models

### Storage

-   local filesystem
-   SQLite
-   PostgreSQL
-   object storage where required

### Deployment

-   serverless
-   PaaS
-   persistent VMs
-   container environments

### Supporting Services

-   Git hosting
-   monitoring
-   secrets
-   authentication
-   DNS/CDN
-   CI/CD

## 5.2 Durable vs Expiring Resources

Resources are divided into:

### Durable Backbone

Resources suitable for long-term architecture.

Examples include:

-   GitHub
-   GitHub Actions
-   free PaaS/serverless layers
-   free database tiers
-   persistent low-cost/free CPU
-   renewable student benefits
-   multiple free inference providers

### Expiring Ammunition

Resources whose availability or credits should never become
architectural dependencies.

Examples:

-   Azure credits
-   temporary cloud trials
-   promotional model credits
-   GPU credits
-   startup credits
-   time-limited database credits

### Rule

**An expiring resource may accelerate the infrastructure, but its
disappearance must not invalidate the infrastructure.**

------------------------------------------------------------------------

# 19. Resource Lifecycle Policy

Every external resource should have metadata:

``` text
resource_id
provider
type
purpose
status
expiration
quota
cost
dependencies
replacement
criticality
```

## Criticality Classes

### C0 --- Optional

Loss causes no meaningful degradation.

### C1 --- Useful

Loss reduces capability but system continues.

### C2 --- Important

Loss requires fallback.

### C3 --- Critical

Loss threatens a core capability.

No external provider should ideally remain C3 indefinitely.

------------------------------------------------------------------------

# 20. Provider Failure Strategy

The infrastructure must assume:

-   providers change prices;
-   free tiers disappear;
-   models are retired;
-   quotas change;
-   APIs break;
-   accounts are suspended;
-   services experience outages.

Therefore:

``` text
Provider failure
      ↓
Health detection
      ↓
Retry if appropriate
      ↓
Fallback provider
      ↓
Capability degradation
      ↓
Operator notification
```

The desired failure mode is:

> **degraded capability, not total system failure.**

------------------------------------------------------------------------

# 52. Infrastructure Resource Strategy — Expanded

## 52.1 Resource Pool

The infrastructure should maintain a registry across:

```text
models
compute
storage
databases
deployment
CI/CD
secrets
monitoring
domains
DNS/CDN
GPU
automation
```

## 52.2 Claim vs Activation

Student resources have different clocks.

Separate:

```text
CLAIM NOW
```

from:

```text
ACTIVATE NOW
```

A benefit can be secured without immediately consuming a time-limited trial.

This distinction must be represented in the resource registry.

## 52.3 Resource States

```text
DISCOVERED
ELIGIBLE
CLAIMED
ACTIVE
DORMANT
EXPIRING
EXPIRED
REPLACED
```

## 52.4 Expiration Tracking

Every temporary resource must have:

- activation date;
- expiration date;
- remaining balance;
- intended use;
- replacement;
- migration plan.

---

# 53. Azure Strategy — Expanded

Azure is explicitly classified as **burst capital**, not the permanent backbone.

Student credits cannot be assumed to cover:

- Azure OpenAI;
- Marketplace third-party software;
- paid DevOps services;
- ExpressRoute;
- support plans.

GPU quota is a separate risk and may require approval.

Therefore the infrastructure should check quota and eligibility **before** designing workloads around Azure GPU.

## 53.1 Appropriate Azure Uses

Potential high-value uses:

- short GPU experiments if quota is approved;
- temporary high-compute jobs;
- staging;
- controlled deployment sprints;
- temporary persistent services;
- database experiments;
- CI/CD workloads;
- burst inference where the specific service is eligible.

## 53.2 Azure Exit Rule

Any service created with expiring credits must have a documented exit path:

```text
Azure resource
    ↓
export / backup
    ↓
alternative provider
    ↓
migration test
    ↓
shutdown
```

---

# 54. Free Backbone Strategy

The student report identifies a broad $0/month baseline containing candidates for:

```text
Git + CI/CD
Domains + DNS
Frontend
API
Database
Authentication
Secrets
Monitoring
LLM inference
GPU notebooks
Persistent CPU
Scraping
```

Candidate services include:

- GitHub Pro / Actions;
- Cloudflare DNS/CDN/Workers;
- Vercel / Netlify;
- Render;
- Supabase / Neon / MongoDB Atlas;
- Clerk;
- Doppler / 1Password;
- Sentry / New Relic;
- Groq / Cerebras / Gemini / Mistral / Hugging Face / OpenRouter;
- Kaggle / Colab;
- Oracle Cloud Always Free;
- Zyte Scrapy Cloud.

These are **resource candidates**, not architectural dependencies.

---

# 55. Free-Tier Failure Assumptions

The free baseline has real constraints:

- sleeping services;
- suspended databases;
- cold starts;
- egress caps;
- GPU scarcity;
- rate limits;
- no always-on large-model GPU;
- limited storage;
- provider terms changing.

Therefore the infrastructure must distinguish:

```text
FREE
```

from:

```text
PRODUCTION-SUITABLE FOR THIS WORKLOAD
```

A free resource is only promoted to a production role after its failure characteristics are understood.

---

# 56. Student Program Strategy

Student status is a resource-acquisition mechanism, not an architecture.

The infrastructure may exploit legitimate student benefits while the eligibility remains valid.

The resource registry must record:

- eligibility;
- verification method;
- renewal cycle;
- card requirement;
- geographic restrictions;
- activation clock;
- benefit value;
- terms;
- replacement.

## 56.1 Startup / Incubator Path

The research also identifies a separate path:

```text
Student
   ↓
legitimate project / venture
   ↓
university incubator / E-Cell / AIC / startup ecosystem
   ↓
startup cloud programs
```

This must not be conflated with student benefits.

Startup credits are available only when the relevant eligibility conditions are genuinely met.

---

# 57. Cost Architecture

The infrastructure should operate in three economic modes.

## Mode A — $0 Backbone

Use:

- free model tiers;
- local support models;
- free compute;
- free databases;
- free deployment;
- free monitoring;
- student benefits.

## Mode B — Minimal Paid Overflow

Use small paid model spend only when free capacity is exhausted.

## Mode C — Burst Capital

Use:

- Azure credits;
- temporary GPU credits;
- trials;
- startup credits;
- frontier credits

for high-value work that cannot be done efficiently by Mode A/B.

The system should be capable of returning from Mode C to Mode A/B.

---

# 58. Resource Economics

The infrastructure should calculate the value of a resource based on:

```text
capability
×
reliability
×
quota
×
duration
÷
cost
```

This is a conceptual metric, not a final formula.

For temporary credits, also consider:

```text
expiration urgency
+
replacement difficulty
+
migration cost
```

The best resource is not always the one with the largest nominal credit value.

---

## Reference resource portfolio

Neptune's implementation should begin from `06_REGISTRIES/RESOURCE_PORTFOLIO.md` and `02_ARCHITECTURE/10_RESOURCE_PLACEMENT.md`. The student research establishes a durable free backbone plus temporary burst resources; current quotas and eligibility are snapshots and must be reverified before activation.


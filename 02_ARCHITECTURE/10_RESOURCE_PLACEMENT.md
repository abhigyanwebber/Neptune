# Resource Placement Strategy

## 1. Durable free backbone

Prefer durable/free resources for:

- source control;
- CI;
- lightweight persistent services;
- basic data;
- observability;
- secrets;
- edge functions.

## 2. Temporary credit placement

Use temporary credits for work that benefits from burst capacity:

- GPU experiments;
- temporary production deployment;
- large batch processing;
- migration;
- benchmarking;
- short-lived high-compute workloads.

Do not burn expiring credits on workloads that can run indefinitely on free resources.

## 3. Resource selection matrix

| Need | First candidate class | Secondary | Burst |
|---|---|---|---|
| Git/CI | GitHub Student + Actions | Codespaces | Azure if needed |
| Model inference | free external APIs | cheap APIs | frontier/credit lane |
| Persistent CPU | Oracle Always Free | free PaaS | Azure |
| Edge/API | Cloudflare Workers | Render | Azure |
| Relational DB | Supabase/Neon | self-hosted Postgres | Azure |
| Document/operational DB | MongoDB Atlas | relational fallback | Azure |
| Cache/vector | Upstash/Qdrant/Astra free tiers | self-host | Azure |
| Monitoring | Sentry/New Relic | logs | paid only if necessary |
| Secrets | Doppler/GitHub secrets | local secret store | paid only if necessary |
| GPU | Kaggle/Colab | Azure | other legitimate credits |

This table is a placement strategy, not a claim that all resources must be active simultaneously.

## 4. Clock discipline

Resources with activation-triggered expiration should be activated only when the workload is ready.

Permanent or already-running student benefits should be used when useful.

This preserves scarce time-limited resources.

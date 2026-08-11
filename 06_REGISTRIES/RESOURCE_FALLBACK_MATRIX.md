# Resource Fallback Matrix

| Capability | Primary reference | Fallback 1 | Fallback 2 | Must survive without it? |
|---|---|---|---|---|
| Source | GitHub | local Git | alternate Git host | Yes |
| CI | GitHub Actions | local runner | alternate CI | Yes, via local path |
| Persistent CPU | Oracle Always Free | local host | temporary cloud | Yes, reduced mode |
| Relational state | PostgreSQL on reference host | Supabase/Neon | alternate Postgres | Yes, recovery required |
| Inference | free primary lane | free secondary | cheap/escalation | Yes |
| Provider normalization | LiteLLM | alternate adapter | direct adapter for emergency | Yes |
| Runtime | Docker | local process for trusted dev | alternate sandbox | Yes, through contract |
| Monitoring | structured logs | Sentry | New Relic/other telemetry | Yes |
| Secrets | environment/local secret store | GitHub secrets | Doppler | Yes |
| Backup | object-storage adapter | local encrypted backup | alternate object store | No single target may be sole copy |
| Edge | Cloudflare | direct host | alternate reverse proxy | Yes |

## Rule

Fallbacks are capability replacements, not necessarily identical vendors.

The system should degrade by capability rather than collapse because one product disappears.

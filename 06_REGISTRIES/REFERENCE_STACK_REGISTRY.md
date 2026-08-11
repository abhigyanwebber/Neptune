# Reference Stack Registry

**Status:** First-build reference. External availability must be revalidated at activation time.

| Layer | Reference | Purpose | Failure replacement |
|---|---|---|---|
| Source/CI | GitHub + Actions | source, checks, release | another Git provider/CI adapter |
| Host | Oracle Always Free candidate | persistent lightweight services | local / another VPS / temporary cloud |
| Edge | Cloudflare candidate | DNS, proxy, edge | direct host / another proxy |
| API | FastAPI | control/API surface | another HTTP implementation |
| State | PostgreSQL | durable relational state | managed/self-hosted Postgres |
| Data access | SQLAlchemy | repository implementation | alternate repository adapter |
| Model gateway | Neptune gateway | provider-neutral inference | none; contract is mandatory |
| Provider normalization | LiteLLM | provider protocol normalization | alternate normalization adapter |
| Model supply | verified free candidates | inference | any capability-compatible candidate |
| Runtime | Docker | sandboxed execution baseline | alternate runtime adapter |
| Observability | OpenTelemetry + Sentry candidate | traces/errors | other telemetry stack |
| Secrets | GitHub secrets / Doppler candidate | secret delivery | alternate secret provider |
| Backup | object-storage adapter | durable backup | alternate backup target |

## Supply lanes

The exact model name is not part of this registry's stable identity. Entries should be represented by capability and current provider facts.

```yaml
lane: free_primary
required_capabilities: [reasoning, planning]
cost_class: free
durability: candidate
fallbacks: [free_secondary, cheap_overflow]
```

```yaml
lane: free_fast
required_capabilities: [tool_use, coding]
cost_class: free
dual_home_preferred: true
fallbacks: [free_secondary, cheap_overflow]
```

```yaml
lane: cheap_overflow
cost_class: cheap
activation: explicit
fallbacks: [escalation, queue]
```

```yaml
lane: escalation
cost_class: temporary_or_paid
activation: explicit
budget_required: true
```

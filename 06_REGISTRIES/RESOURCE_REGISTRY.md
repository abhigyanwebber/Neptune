# Resource Registry

## Resource states

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

## Required fields

```yaml
id:
name:
provider:
resource_type:
criticality:
eligibility:
claimed_at:
activated_at:
expires_at:
remaining_balance:
renewal:
cost:
intended_use:
project_mapping:
replacement:
exit_plan:
verification_date:
status:
```

## Criticality classes

- **R0 Disposable** — cache/temp.
- **R1 Recoverable** — sessions/temp artifacts.
- **R2 Important** — agent state, task records, event logs.
- **R3 Critical** — infrastructure configuration, architecture, provider registry, secret metadata.

## Claim vs activation

A benefit may be claimable without immediately activating a time-limited clock. The registry must represent both states separately.


## Implementation-facing portfolio

See `06_REGISTRIES/RESOURCE_PORTFOLIO.md` for the consolidated student/free/cheap resource inventory and economic classification.

# Provider Registry

Provider records are operational data.

## Required fields

```yaml
id:
name:
provider_type:
regions: []
endpoints: []
capabilities: []
pricing_snapshot:
quota_snapshot:
health:
verification_date:
terms_url:
status:
failure_history:
fallback_providers: []
cache_characteristics:
notes:
```

## Reliability categories

- `STRUCTURAL` — acceptable as a backbone lane after validation.
- `BONUS` — useful but may disappear.
- `BURST` — intentionally temporary.
- `LOCAL` — on-device support.
- `RETIRED` — no longer used.

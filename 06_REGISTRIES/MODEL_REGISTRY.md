# Model Registry

**Status:** Candidate registry structure. Current provider entries are snapshots and must be revalidated before use.

## Capability classes

- `fast_general`
- `coding`
- `reasoning`
- `planning`
- `summarization`
- `classification`
- `tool_use`
- `vision`
- `embedding`
- `frontier_escalation`

## Role classes

| Role | Desired properties |
|---|---|
| Router | fast, structured |
| Classifier | cheap, stable |
| Context compressor | cheap, reliable |
| Extraction worker | throughput |
| Coder | coding specialization |
| Planner | reasoning depth |
| Reviewer | independent verification |
| Debugger | diagnosis |
| Escalation | highest available quality |

## Snapshot candidates from R01

The report's verified snapshot identified:
- Gemini free lane;
- Groq;
- Cerebras;
- Mistral;
- Cloudflare Workers AI;
- NVIDIA NIM credits;
- OpenRouter `:free` as bonus/ephemeral;
- local small models as support/fallback.

Do not interpret this list as a guarantee of present availability.

## Required record fields

```yaml
id:
provider:
model:
capabilities: []
context_limit:
tool_calling:
structured_output:
cost_class:
quota:
health:
availability:
verified_at:
fallbacks: []
preferred_roles: []
notes:
```


## Implementation-facing catalog

See `06_REGISTRIES/MODEL_SUPPLY_CATALOG.md` for the report-derived lane assignments and failure-aware usage guidance.

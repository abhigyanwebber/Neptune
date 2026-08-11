# Model Supply Topology

The model layer is a supply chain, not a single model.

## Logical topology

```text
                 MODEL GATEWAY
                       |
                CAPABILITY ROUTER
                       |
      +----------------+----------------+
      |                |                |
   FREE LANES      CHEAP LANE      ESCALATION
      |                |                |
 Gemini/Groq/       Qwen/DeepSeek/   frontier or
 Cerebras/Mistral   Mistral-class    strongest available
 Cloudflare/NIM/
 OpenRouter bonus
      |
   local support
```

## Supply invariants

1. Core agent logic does not know provider-specific credentials.
2. Models are selected by capability, not by hard-coded project logic.
3. A model identity should have fallback providers where possible.
4. Provider health and quota are observable.
5. A free model may disappear without invalidating the architecture.
6. Paid escalation is optional, not foundational.
7. Local inference is a support tier on the current hardware.

## Capability pinning

A lane should pin a capability profile rather than blindly pinning a model name.

Example:

```yaml
lane: coding
requirements:
  tool_calling: true
  structured_output: preferred
  context_class: large
  quality_floor: coding-medium
providers:
  - current_candidate_1
  - current_candidate_2
```

The exact representation is implementation-defined.

## Dual-homing

Where the same open-weight model is available through multiple providers, prefer that arrangement because provider failure then does not necessarily change model behavior.

## Safe switching

Do not assume model switching is state-free.

Switch at:

- new task;
- new turn;
- compaction boundary;
- explicit escalation boundary.

Avoid switching mid-generation.

## Quota engineering

Quota is part of routing.

The router should understand:

- requests/minute;
- tokens/minute;
- daily allowances;
- provider cooldown;
- remaining temporary credits.

The numbers are registry snapshots, not architectural constants.

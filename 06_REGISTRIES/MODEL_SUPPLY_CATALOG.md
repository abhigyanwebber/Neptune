# Model Supply Catalog

This catalog translates the LLM research report into implementation-facing model classes.

## Primary free

### Gemini Flash family
Use for:
- planning;
- general reasoning;
- research;
- sustained free agent work.

Reason:
The report identifies Gemini Flash as the strongest genuinely free primary engine in the verified snapshot, with unusually large context and high free throughput.

## Dual-home free coding/tool lane

### GPT-OSS family
Preferred where available through:
- Groq;
- Cerebras;
- NVIDIA.

Use for:
- coding;
- tool calling;
- bounded agent work;
- fallback.

Reason:
The same model identity across providers reduces behavioral drift when a provider fails.

## Coding specialist

### Qwen-Coder family / GLM coding-class models
Use for:
- patch generation;
- code generation;
- debugging;
- coding-heavy turns.

Reason:
The report found coding-specialized models outperform similarly sized general models on agentic coding tasks.

## Cheap overflow

Candidate families:
- Qwen flash/class;
- DeepSeek Flash;
- Mistral small/class.

Use when free quotas bind.

## Local support

Candidate:
- small Qwen-Coder-class model;
- Phi-class classifier.

Use for:
- classification;
- summarization;
- context compression;
- offline work.

The current laptop should not be treated as the main inference node.

## Bonus/temporary

- OpenRouter `:free`
- NVIDIA NIM credits
- Alibaba one-time model grants where still available
- legitimate xAI signup/promotional credits

These are not baseline dependencies.

## Capability records

Every active model must record:

```yaml
provider
model_id
capabilities
tool_calling
structured_output
context_class
cost_class
quota_class
verification_date
fallbacks
failure_modes
```

## Model selection rule

The model registry stores what exists.

The router decides what should be used.

The agent should not contain provider-specific model selection logic.

# Project Integration Boundary

The infrastructure is project-agnostic.

A project should declare:

```text
project_id
required_capabilities
task_types
tools
memory_scope
data stores
security profile
deployment profile
resource budget
observability requirements
```

The project must not redefine:

- model gateway semantics;
- task/session semantics;
- core permission semantics;
- core event schema;
- resource lifecycle semantics.

## Research-derived mappings

### Argus

The harness report maps Argus toward:
- OpenHands for multi-agent substrate;
- Goose for MCP/general agent patterns;
- Aider as a coding/reference harness;
- research orchestration patterns.

Argus-specific evidence acquisition, taxonomy and research logic remain outside this reusable infrastructure.

### Workspace OS

The harness report maps Workspace OS toward:
- Aider;
- Gemini CLI;
- Codex CLI;
- Kilo/Memory Bank;
- Qwen Code daemon patterns.

The SaaS product logic remains outside the reusable infrastructure.

### Generic agent/automation

Candidate patterns:
- Goose;
- Continue;
- Cline connectors/cron.

These are reference patterns, not mandatory dependencies.

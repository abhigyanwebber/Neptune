# Threat Model

## Core assumption

The model's intent is not a security boundary.

Anything an agent reads may contain attacker-controlled instructions.

## Primary threats

1. Prompt injection in repositories, READMEs, issues, PRs and web pages.
2. Malicious MCP configuration.
3. Tool abuse.
4. Secret exposure.
5. Destructive shell commands.
6. Remote Git destruction.
7. Production database changes.
8. Supply-chain attacks through packages/plugins/skills.
9. Malicious lifecycle scripts.
10. Sandbox escape or insufficient isolation.
11. Untrusted output being fed into package publication/cache workflows.
12. Resource exhaustion through oversized tool output or loops.

## Trust boundaries

```text
USER
 ↓
TASK
 ↓
MODEL  ← untrusted reasoning source
 ↓
POLICY / PERMISSION ENGINE
 ↓
SANDBOX
 ↓
TOOLS
 ↓
EXTERNAL SYSTEMS
```

The model is inside the trust boundary only as a source of proposed actions, never as the final authority.

## Security invariants

- least privilege;
- sandbox first;
- credentials minimized;
- external effects auditable;
- destructive operations reversible where possible;
- explicit escalation for high-risk actions;
- untrusted inputs remain untrusted.

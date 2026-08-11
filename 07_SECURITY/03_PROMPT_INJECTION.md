# Prompt Injection and Tool Security

## Source-derived lesson

The harness research documents that prompt injection is systemic across agent systems, including attacks through MCP configuration and untrusted project content. It also records incidents involving destructive Git actions and production database migration attempts.

## Required handling

Treat as attacker-controlled:

- README files;
- source comments;
- issue descriptions;
- pull requests;
- web pages;
- MCP configuration;
- package metadata;
- generated files;
- skill/plugin content.

## Rules

1. Never run auto-approve/yolo mode on untrusted repositories.
2. Isolate untrusted projects in worktrees, containers or VMs.
3. Keep secret-bearing environment variables out of agent sessions.
4. Do not let agent output directly publish packages.
5. Do not let agent output directly mutate caches used as trusted inputs.
6. Require review for destructive or production actions.
7. Log the source and provenance of instructions used to authorize external effects.

## Security experiment backlog

- prompt injection through README;
- malicious MCP server;
- malicious package lifecycle script;
- secret exfiltration attempt;
- destructive Git command;
- production migration attempt;
- oversized tool output;
- sandbox escape attempt.

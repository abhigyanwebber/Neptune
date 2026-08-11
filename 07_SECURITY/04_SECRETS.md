# Secrets Architecture

## Rule

Secrets are infrastructure-managed resources, not ordinary model context.

## Requirements

- never inject unnecessary secrets into model-visible context;
- scope credentials to the smallest capability;
- use ephemeral credentials where possible;
- separate development/staging/production secrets;
- redact secrets from logs and artifacts;
- audit secret access;
- prohibit secret export through ordinary tools;
- maintain metadata/backups without exposing secret values.

## Candidate external tooling from research

- Doppler
- 1Password

These are resource candidates, not architectural dependencies.

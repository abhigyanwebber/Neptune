# ADR-032 — Model Gateway Owns Provider Independence

## Decision
Neptune's Model Gateway is the stable internal inference boundary. LiteLLM is used behind that boundary for provider normalization/routing transport in the reference implementation.

## Rationale
The research found LiteLLM to be a strong self-hosted proxy and emphasized that a router/control plane is essential for fragile free-tier supply.

## Consequence
Replacing LiteLLM or a provider must not require changes to agent/application logic.

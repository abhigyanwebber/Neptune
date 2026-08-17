"""Provider-neutral vocabulary.

Values are drawn from 06_REGISTRIES/MODEL_REGISTRY.md so the gateway,
router, registry and adapters share one closed vocabulary instead of
free-text strings. Agent logic requests capabilities, never provider
or model names (01_BIBLE/16_FINAL_IMPLEMENTATION_SPEC.md section 7 /
ADR-024).
"""

from __future__ import annotations

from enum import Enum


class Capability(str, Enum):
    """Capability classes, per MODEL_REGISTRY.md."""

    FAST_GENERAL = "fast_general"
    CODING = "coding"
    REASONING = "reasoning"
    PLANNING = "planning"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    TOOL_USE = "tool_use"
    VISION = "vision"
    EMBEDDING = "embedding"
    FRONTIER_ESCALATION = "frontier_escalation"


class CostClass(str, Enum):
    """Cost tiers, per RESOURCE_ECONOMIC_CLASSIFICATION.md and
    06_REGISTRIES/MODEL_REGISTRY.md `cost_class` field."""

    FREE = "free"
    CHEAP = "cheap"
    PAID = "paid"
    FRONTIER = "frontier"


class Availability(str, Enum):
    """Provider/model availability, per PROVIDER_REGISTRY.md `status`."""

    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    RETIRED = "retired"


class HealthStatus(str, Enum):
    """Coarse health signal surfaced by a provider adapter, per
    PROVIDER_CONTRACT.md ("expose health/availability information
    where possible")."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ErrorType(str, Enum):
    """Normalized, provider-independent error classification so core
    never has to interpret a provider-specific error code."""

    RATE_LIMITED = "rate_limited"
    QUOTA_EXCEEDED = "quota_exceeded"
    TIMEOUT = "timeout"
    INVALID_REQUEST = "invalid_request"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    AUTHENTICATION = "authentication"
    UNKNOWN = "unknown"

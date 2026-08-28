"""Capability Vocabulary Bridge (C-006).

Translation boundary between the legacy/B-side capability vocabulary
(neptune.core.domain.capability.Capability -- a closed Python Enum) and
the canonical capability vocabulary
(core.registry.capability_registry.KNOWN_CAPABILITIES -- Neptune's
authoritative source of truth as of ADR-041/ADR-042).

This module deliberately does NOT import
`neptune.core.domain.capability.Capability` or anything else from
`src/neptune` -- the bridge operates on plain strings on both sides, so
`src/core` never depends on a B-side enum (or any provider-specific
type). A future caller on the Neptune/B side is expected to pass
`Capability.CODING.value` (a plain str) in, and to convert this
function's plain-str output back to its own enum if it needs to, e.g.
`Capability(bridge_output)` -- that conversion happens on the caller's
side, not in `src/core`.

Mapping data (C-006 inspection, verified directly against the actual
enum in src/neptune/core/domain/capability.py, not assumed from earlier
reports): of the legacy vocabulary's 10 values, 8 already match a
canonical capability_id by exact string identity (coding, reasoning,
planning, summarization, classification, tool_use, vision, embedding --
the last 3 of these were added to the canonical vocabulary specifically
*because* of this overlap, during C-004/ADR-042). The remaining 2
(`fast_general`, `frontier_escalation`) were explicitly evaluated and
rejected as capability-vocabulary members by ADR-042 -- they describe a
cost/latency tier and a routing/escalation policy respectively, not a
task-type capability. This module does not re-litigate that decision;
it enforces it, giving the rejection a specific, explanatory error
instead of a generic "unknown" one.

No new architectural decision is made here (see DEVELOPMENT_STATE
C-DEC entry for this task) -- this module mechanically implements the
translation ADR-042 already decided the shape of.
"""
from __future__ import annotations

from typing import Iterable

from .capability_registry import KNOWN_CAPABILITIES

# 1:1 mappings, external (legacy/B-side) capability name -> canonical
# capability_id. Values on both sides are verified identical strings
# today, but this table is the explicit translation boundary the task
# requires rather than relying on that coincidence implicitly -- if
# either vocabulary's spelling ever diverges, only this table changes.
EXTERNAL_TO_CANONICAL: dict[str, str] = {
    "coding": "coding",
    "reasoning": "reasoning",
    "planning": "planning",
    "summarization": "summarization",
    "classification": "classification",
    "tool_use": "tool_use",
    "vision": "vision",
    "embedding": "embedding",
}

# Known external capability names that are deliberately NOT translated --
# ADR-042 already decided these are not capability-vocabulary concepts.
# Kept as an explicit table (not just "anything not in EXTERNAL_TO_CANONICAL
# is unknown") so callers get a specific, actionable reason rather than a
# generic unknown-capability error.
REJECTED_EXTERNAL_CAPABILITIES: dict[str, str] = {
    "fast_general": (
        "describes a cost/latency performance tier, not a task-type "
        "capability -- overlaps with CostClass instead. Rejected by ADR-042."
    ),
    "frontier_escalation": (
        "describes a routing/escalation policy (see ADR-006 'Explicit "
        "escalation'), not a capability fact about a model. Rejected by "
        "ADR-042."
    ),
}


class UnknownExternalCapabilityError(ValueError):
    """Raised for an external capability name the bridge has never heard
    of -- neither a known mapping, a known rejection, nor already a
    canonical id. Mirrors the naming/shape of
    core.registry.capability_registry.UnknownCapabilityError so both
    "unknown to the registry" and "unknown to the bridge" fail the same
    way for a caller that doesn't care which layer raised."""


class RejectedExternalCapabilityError(ValueError):
    """Raised for an external capability name the bridge recognizes but
    has deliberately decided is not a canonical capability (ADR-042).
    Distinct from UnknownExternalCapabilityError because the caller may
    want to handle "this will never translate" differently from "this
    might be a typo or a new capability we haven't reconciled yet"."""


def translate_capability(external_capability_id: str) -> str:
    """Translate one external (legacy/B-side) capability name into its
    canonical capability_id.

    Canonical passthrough: if `external_capability_id` is already a
    canonical id (e.g. "web_search", which has no external/B-side
    representation at all), it is returned unchanged -- the bridge is
    idempotent for anything already on the canonical side, so callers
    don't need to know in advance which vocabulary a given string came
    from.

    Raises RejectedExternalCapabilityError for a recognized-but-rejected
    name (fast_general, frontier_escalation), or
    UnknownExternalCapabilityError for anything else unrecognized by
    either vocabulary. Never returns a value outside KNOWN_CAPABILITIES.
    """
    if external_capability_id in EXTERNAL_TO_CANONICAL:
        canonical_id = EXTERNAL_TO_CANONICAL[external_capability_id]
        assert canonical_id in KNOWN_CAPABILITIES  # translation table must never drift from the canonical set
        return canonical_id

    if external_capability_id in KNOWN_CAPABILITIES:
        return external_capability_id

    if external_capability_id in REJECTED_EXTERNAL_CAPABILITIES:
        raise RejectedExternalCapabilityError(
            f"'{external_capability_id}' is not translated to a canonical capability: "
            f"{REJECTED_EXTERNAL_CAPABILITIES[external_capability_id]}"
        )

    raise UnknownExternalCapabilityError(
        f"'{external_capability_id}' is not a recognized external capability name "
        f"(known external names: {sorted(EXTERNAL_TO_CANONICAL)}; "
        f"known canonical ids: {sorted(KNOWN_CAPABILITIES)})"
    )


def translate_capabilities(external_capability_ids: Iterable[str]) -> list[str]:
    """Translate a batch, de-duplicating canonical output while
    preserving first-seen order -- so two external names that both map
    to the same canonical id (a real possibility once a vocabulary has
    synonyms) don't silently produce a duplicate canonical entry.
    Raises on the first unrecognized/rejected name, same as
    translate_capability()."""
    seen: set[str] = set()
    result: list[str] = []
    for external_id in external_capability_ids:
        canonical_id = translate_capability(external_id)
        if canonical_id not in seen:
            seen.add(canonical_id)
            result.append(canonical_id)
    return result

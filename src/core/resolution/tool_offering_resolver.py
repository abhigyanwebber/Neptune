"""Dynamic, registry-driven tool offering (A-008).

Resolves "what tools should be offered to the model this request" purely
from the canonical Tool Registry (core.registry.tool_registry.ToolRegistry,
A-003) -- the same registry that is already Neptune's single source of
truth for tool *vocabulary*. TOOL_CONTRACT.md's invariant ("tool
existence does not grant permission") applies unchanged here: this
resolver answers "what tools currently exist," never "is this tool
allowed to run" -- that remains entirely out of scope, per A-008's
explicit exclusion of permissions/sandboxing.

This closes the gap DIRECTOR_REVIEW_002.md / DIRECTOR_REVIEW_003.md /
ADR-046 identified: `ModelGatewayAdapter` previously held a fixed tool
list set once at construction, because nothing existed to derive one
dynamically. This resolver is that missing piece -- Core exposes it as a
plain function over plain data (dicts in, dicts out); the ModelGateway
adapter (Neptune-side, outside core/) remains responsible for
translating its output into whatever provider-facing request shape it
needs, the same "opaque dict boundary" every other Core/Neptune seam in
this project already uses.

Reuses the C-006 capability bridge for any capability-based filtering,
so an external (legacy) capability name can be used to filter without
reintroducing the legacy enum into core/.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

from core.registry.capability_bridge import (
    RejectedExternalCapabilityError,
    UnknownExternalCapabilityError,
    translate_capability,
)
from core.registry.tool_registry import ToolDefinition, ToolRegistry


class ToolOfferingResolver:
    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._tools = tool_registry

    def available_tools(self, capability_ids: Optional[Iterable[str]] = None) -> list[dict[str, Any]]:
        """Returns the canonical tools currently registered, as plain
        dicts, deterministically ordered by tool_id. Never fabricates a
        placeholder -- an empty registry, or a capability filter that
        matches nothing, both correctly produce [] rather than a fake
        entry (A-008 requirement: "do not insert fake placeholder
        tools").

        Queries the registry fresh on every call (no caching) --
        registering, updating, or deleting a tool is reflected on the
        very next call, with no separate invalidation step needed.

        `capability_ids`, if given, may be external (legacy) or
        canonical capability names -- each is translated through the
        C-006 bridge before filtering. An individual unrecognized or
        rejected capability id within the filter set is excluded from
        the effective filter (not raised) so one bad entry in a list of
        several doesn't discard the valid ones; if every entry in
        `capability_ids` is invalid, the effective filter is empty and
        the result is correctly [] (nothing matches an empty capability
        set), not an error.
        """
        canonical_capability_ids: Optional[set[str]] = None
        if capability_ids is not None:
            canonical_capability_ids = self._safe_translate_all(capability_ids)

        tools = self._tools.list_all()
        if canonical_capability_ids is not None:
            tools = [t for t in tools if t.capability in canonical_capability_ids]

        # Deterministic order + defensive de-duplication. The registry's
        # own primary key already guarantees id-uniqueness for any
        # SQLAlchemy-backed repository, but this resolver does not
        # assume every current or future ToolRepository implementation
        # enforces that -- de-duplicating here is cheap and makes the
        # guarantee independent of the storage layer.
        seen: set[str] = set()
        offerings: list[dict[str, Any]] = []
        for tool in sorted(tools, key=lambda t: t.tool_id):
            if tool.tool_id in seen:
                continue
            seen.add(tool.tool_id)
            offerings.append(_to_offering_dict(tool))
        return offerings

    def get_offering(self, tool_id: str) -> Optional[dict[str, Any]]:
        """A single tool's offering dict, or None if `tool_id` is not
        registered -- unknown tools fail safely (a clear "not found"
        rather than a fabricated entry)."""
        tool = self._tools.get(tool_id)
        return _to_offering_dict(tool) if tool else None

    @staticmethod
    def _safe_translate_all(capability_ids: Iterable[str]) -> set[str]:
        translated: set[str] = set()
        for capability_id in capability_ids:
            try:
                translated.add(translate_capability(capability_id))
            except (UnknownExternalCapabilityError, RejectedExternalCapabilityError):
                continue
        return translated


def _to_offering_dict(tool: ToolDefinition) -> dict[str, Any]:
    return {
        "tool_id": tool.tool_id,
        "name": tool.name,
        "capability": tool.capability,
        "description": tool.notes or tool.name,
        "risk_class": tool.risk_class,
    }

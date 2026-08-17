"""Tool catalog.

Fixed vocabulary per director's brief: browser, terminal, filesystem,
search, mcp. Catalog record only -- TOOL_CONTRACT.md invariant: "Tool
existence does not grant permission." Registering a tool here says nothing
about whether any agent is authorized to use it; that is the future
Permission/Sandbox layer's job.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

from .audit import emit_registry_event

if TYPE_CHECKING:  # pragma: no cover
    from core.contracts.registry import ToolDefinitionRepository
    from core.contracts.repositories import EventRepository

KNOWN_TOOLS: frozenset[str] = frozenset({"browser", "terminal", "filesystem", "search", "mcp"})


class UnknownToolError(ValueError):
    pass


@dataclass
class ToolDefinition:
    tool_id: str
    name: str
    capability: str = ""
    risk_class: Optional[str] = None
    depends_on: list[str] = field(default_factory=list)
    verification_date: Optional[str] = None
    notes: Optional[str] = None
    # Verification metadata (A-004), additive.
    verification_source: Optional[str] = None
    verification_status: Optional[str] = None
    last_checked: Optional[str] = None


class ToolRegistry:
    def __init__(
        self,
        repository: "ToolDefinitionRepository",
        strict: bool = True,
        event_repo: "Optional[EventRepository]" = None,
    ) -> None:
        self._repo = repository
        self._strict = strict
        self._events = event_repo

    def register(self, tool: ToolDefinition) -> None:
        if self._strict and tool.tool_id not in KNOWN_TOOLS:
            raise UnknownToolError(
                f"'{tool.tool_id}' is not in the known tool vocabulary: {sorted(KNOWN_TOOLS)}"
            )
        self._repo.create(tool)
        emit_registry_event(self._events, "registry.tool.registered", tool.tool_id)

    def get(self, tool_id: str) -> Optional[ToolDefinition]:
        return self._repo.get(tool_id)

    def update(self, tool: ToolDefinition) -> None:
        self._repo.update(tool)
        emit_registry_event(self._events, "registry.tool.updated", tool.tool_id)

    def delete(self, tool_id: str) -> None:
        self._repo.delete(tool_id)
        emit_registry_event(self._events, "registry.tool.deleted", tool_id)

    def list_all(self) -> list[ToolDefinition]:
        return self._repo.list_all()

    def find_by_capability(self, capability_id: str) -> list[ToolDefinition]:
        return [t for t in self._repo.list_all() if t.capability == capability_id]

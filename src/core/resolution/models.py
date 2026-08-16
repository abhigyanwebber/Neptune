"""Resolution result type.

A ResolutionResult is a pure data record describing what the resolution
layer decided -- never what it *did*. Nothing in core/resolution executes
a provider call, runs a tool, or performs any runtime action (A-006
brief); this is selection logic that sits between Runtime Intent and
Registry Lookup, one step upstream of any real execution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from core.registry.provider_registry import Provider


@dataclass
class ResolutionResult:
    capability: str
    provider: Optional[Provider] = None
    dependencies: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

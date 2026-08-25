"""Registry Snapshot Export (A-004).

Exports the complete state of all four registries to a single JSON
document -- for provider migration (standing up a new Neptune instance
with the same catalog) and disaster recovery (Postgres is gone; rebuild
the registry from the last snapshot).

Pure data transformation: takes already-constructed registry service
objects and calls their existing list_all() methods, so this has no
opinion about where those registries get their data from.
"""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .capability_registry import CapabilityRegistry
from .model_registry import ModelRegistry
from .provider_registry import ProviderRegistry
from .resource_registry import ResourceRegistry
from .tool_registry import ToolRegistry

# 1.1: added the optional "models" section (C-004). 1.0 consumers reading
# only capabilities/providers/resources/tools are unaffected -- the new
# section is additive and simply absent when no ModelRegistry is supplied.
SNAPSHOT_SCHEMA_VERSION = "1.1"


def export_registry_snapshot(
    capability_registry: CapabilityRegistry,
    provider_registry: ProviderRegistry,
    resource_registry: ResourceRegistry,
    tool_registry: ToolRegistry,
    model_registry: Optional[ModelRegistry] = None,
) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "capabilities": [dataclasses.asdict(c) for c in capability_registry.list_all()],
        "providers": [dataclasses.asdict(p) for p in provider_registry.list_all()],
        "resources": [dataclasses.asdict(r) for r in resource_registry.list_all()],
        "tools": [dataclasses.asdict(t) for t in tool_registry.list_all()],
    }
    if model_registry is not None:
        snapshot["models"] = [dataclasses.asdict(m) for m in model_registry.list_all()]
    return snapshot


def export_registry_snapshot_to_file(
    path: Path,
    capability_registry: CapabilityRegistry,
    provider_registry: ProviderRegistry,
    resource_registry: ResourceRegistry,
    tool_registry: ToolRegistry,
    model_registry: Optional[ModelRegistry] = None,
) -> Path:
    snapshot = export_registry_snapshot(
        capability_registry, provider_registry, resource_registry, tool_registry, model_registry
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True)
    return path

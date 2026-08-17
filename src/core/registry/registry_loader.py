"""Registry Import Framework (A-004).

Loads providers.yaml / tools.yaml / resources.yaml / capabilities.yaml
into the four registries. Upsert semantics: an entry whose id already
exists is updated, otherwise it is registered fresh -- so the same YAML
file can be re-applied safely (e.g. after editing verification metadata)
without raising "already exists" errors.

This module only depends on the registry *service* classes (which
themselves depend only on repository Protocols), so it stays
persistence-agnostic -- it will load into a SQLite-backed registry in
tests exactly the same way it loads into a Postgres-backed one in
production.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any, Callable, TypeVar

import yaml

from .capability_registry import Capability, CapabilityRegistry
from .provider_registry import Provider, ProviderRegistry
from .resource_registry import Resource, ResourceRegistry
from .tool_registry import ToolDefinition, ToolRegistry

T = TypeVar("T")


@dataclasses.dataclass
class LoadResult:
    registered: list[str] = dataclasses.field(default_factory=list)
    updated: list[str] = dataclasses.field(default_factory=list)
    errors: list[str] = dataclasses.field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.registered) + len(self.updated)


def _read_entries(path: Path, top_level_key: str) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    entries = data.get(top_level_key, [])
    if not isinstance(entries, list):
        raise ValueError(f"{path}: expected a list under '{top_level_key}'")
    return entries


def _load_entries(
    path: Path,
    top_level_key: str,
    id_field: str,
    record_cls: type[T],
    get_fn: Callable[[str], Any],
    register_fn: Callable[[T], None],
    update_fn: Callable[[T], None],
) -> LoadResult:
    result = LoadResult()
    known_fields = {f.name for f in dataclasses.fields(record_cls)}

    for raw in _read_entries(path, top_level_key):
        entry_id = raw.get(id_field)
        if not entry_id:
            result.errors.append(f"entry missing '{id_field}': {raw!r}")
            continue

        # Ignore unknown keys rather than failing the whole load -- YAML
        # authored by B or the director may carry extra descriptive keys
        # (e.g. free-text commentary) that aren't registry fields.
        filtered = {k: v for k, v in raw.items() if k in known_fields}
        try:
            record = record_cls(**filtered)  # type: ignore[call-arg]
        except TypeError as exc:
            result.errors.append(f"{entry_id}: {exc}")
            continue

        try:
            if get_fn(entry_id) is not None:
                update_fn(record)
                result.updated.append(entry_id)
            else:
                register_fn(record)
                result.registered.append(entry_id)
        except Exception as exc:  # noqa: BLE001 - record and continue
            result.errors.append(f"{entry_id}: {exc}")

    return result


def load_capabilities(path: Path, registry: CapabilityRegistry) -> LoadResult:
    return _load_entries(
        path, "capabilities", "capability_id", Capability, registry.get, registry.register, registry.update
    )


def load_providers(path: Path, registry: ProviderRegistry) -> LoadResult:
    return _load_entries(
        path, "providers", "provider_id", Provider, registry.get, registry.register, registry.update
    )


def load_resources(path: Path, registry: ResourceRegistry) -> LoadResult:
    return _load_entries(
        path, "resources", "resource_id", Resource, registry.get, registry.register, registry.update
    )


def load_tools(path: Path, registry: ToolRegistry) -> LoadResult:
    return _load_entries(
        path, "tools", "tool_id", ToolDefinition, registry.get, registry.register, registry.update
    )


def load_registry_directory(
    directory: Path,
    capability_registry: CapabilityRegistry,
    provider_registry: ProviderRegistry,
    resource_registry: ResourceRegistry,
    tool_registry: ToolRegistry,
) -> dict[str, LoadResult]:
    """Loads capabilities.yaml, providers.yaml, resources.yaml, tools.yaml
    from `directory` (any file that doesn't exist is silently skipped, so
    a directory with only some of the four files still loads what's
    there)."""
    return {
        "capabilities": load_capabilities(directory / "capabilities.yaml", capability_registry),
        "providers": load_providers(directory / "providers.yaml", provider_registry),
        "resources": load_resources(directory / "resources.yaml", resource_registry),
        "tools": load_tools(directory / "tools.yaml", tool_registry),
    }

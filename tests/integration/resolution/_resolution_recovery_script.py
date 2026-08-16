"""Standalone script invoked as a SEPARATE OS process by
test_resolution_recovery.py.

    python _resolution_recovery_script.py load_and_resolve
        -> loads the real seed data from 06_REGISTRIES/data/*.yaml into
           Postgres-backed registries, performs resolve_provider("reasoning"),
           prints the result, then this process exits (dies).
    python _resolution_recovery_script.py resolve_only
        -> a brand-new process reconnects (registries already populated by
           the first process) and performs the SAME resolution again,
           proving the result is reproducible from durable registry state
           alone, not from anything held in the first process's memory.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

DATA_DIR = Path(__file__).resolve().parents[3] / "06_REGISTRIES" / "data"

from config.settings import get_database_url  # noqa: E402
from core.registry.capability_registry import CapabilityRegistry  # noqa: E402
from core.registry.provider_registry import ProviderRegistry  # noqa: E402
from core.registry.registry_loader import load_registry_directory  # noqa: E402
from core.registry.resource_registry import ResourceRegistry  # noqa: E402
from core.registry.tool_registry import ToolRegistry  # noqa: E402
from core.resolution.capability_resolver import CapabilityResolver  # noqa: E402
from core.resolution.provider_resolver import ProviderResolver  # noqa: E402
from core.resolution.resource_resolver import ResourceResolver  # noqa: E402
from infrastructure.persistence.database import (  # noqa: E402
    create_all_tables,
    make_engine,
    make_session_factory,
)
from infrastructure.persistence.repositories import (  # noqa: E402
    SqlAlchemyCapabilityRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyToolDefinitionRepository,
)


def _build():
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)
    capabilities = CapabilityRegistry(SqlAlchemyCapabilityRepository(sf))
    providers = ProviderRegistry(SqlAlchemyProviderRepository(sf))
    resources = ResourceRegistry(SqlAlchemyResourceRepository(sf))
    tools = ToolRegistry(SqlAlchemyToolDefinitionRepository(sf))

    capability_resolver = CapabilityResolver(capabilities, providers, tools)
    resource_resolver = ResourceResolver(capabilities, providers, resources, tools)
    provider_resolver = ProviderResolver(capability_resolver, resource_resolver, providers)

    return capabilities, providers, resources, tools, provider_resolver


def _resolve_and_report(provider_resolver) -> dict:
    result = provider_resolver.resolve_provider("reasoning")
    return {
        "capability": result.capability,
        "provider_id": result.provider.provider_id if result.provider else None,
        "dependencies": result.dependencies,
        "eligible_provider_ids": sorted(result.metadata.get("eligible_provider_ids", [])),
        "selection_reason": result.metadata.get("selection_reason"),
    }


def do_load_and_resolve() -> None:
    capabilities, providers, resources, tools, provider_resolver = _build()
    results = load_registry_directory(DATA_DIR, capabilities, providers, resources, tools)
    load_errors = (
        results["capabilities"].errors
        + results["providers"].errors
        + results["resources"].errors
        + results["tools"].errors
    )
    output = _resolve_and_report(provider_resolver)
    output["load_errors"] = load_errors
    print(json.dumps(output))


def do_resolve_only() -> None:
    _capabilities, _providers, _resources, _tools, provider_resolver = _build()
    print(json.dumps(_resolve_and_report(provider_resolver)))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "load_and_resolve":
        do_load_and_resolve()
    elif mode == "resolve_only":
        do_resolve_only()
    else:
        raise SystemExit(f"Unknown mode: {mode}")

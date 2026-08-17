"""Standalone script invoked as a SEPARATE OS process by test_registry_recovery.py.

    python _registry_recovery_script.py write
        -> registers a small provider/resource/tool/capability graph, then
           this process exits (dies).
    python _registry_recovery_script.py read
        -> a brand-new process reconnects and reads back the catalog,
           performs a capability lookup and a dependency resolution, and
           prints the result as JSON.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from config.settings import get_database_url  # noqa: E402
from core.registry.capability_registry import Capability, CapabilityRegistry  # noqa: E402
from core.registry.dependency_resolution import resolve_dependencies  # noqa: E402
from core.registry.provider_registry import Provider, ProviderRegistry  # noqa: E402
from core.registry.resource_registry import Resource, ResourceRegistry  # noqa: E402
from core.registry.tool_registry import ToolDefinition, ToolRegistry  # noqa: E402
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


def _registries():
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return (
        CapabilityRegistry(SqlAlchemyCapabilityRepository(sf)),
        ProviderRegistry(SqlAlchemyProviderRepository(sf)),
        ResourceRegistry(SqlAlchemyResourceRepository(sf)),
        ToolRegistry(SqlAlchemyToolDefinitionRepository(sf)),
    )


def do_write() -> None:
    capabilities, providers, resources, tools = _registries()

    # Idempotency: unlike Task/Session (random uuids per test run), registry
    # ids are fixed vocabulary and Postgres data persists across repeated
    # test runs (docker volume). Clear any leftovers from a prior run first
    # so this script can be re-run safely.
    for cap_id in ("browser", "coding"):
        capabilities.delete(cap_id)
    for res_id in ("docker", "postgres"):
        resources.delete(res_id)
    providers.delete("groq")
    tools.delete("browser")

    capabilities.register(Capability(capability_id="browser", name="Browser capability"))
    capabilities.register(Capability(capability_id="coding", name="Coding capability"))

    resources.register(Resource(resource_id="docker", name="Docker", status="ACTIVE"))
    resources.register(Resource(resource_id="postgres", name="Postgres", status="ACTIVE"))

    providers.register(
        Provider(
            provider_id="groq",
            name="Groq",
            capabilities=["coding", "reasoning"],
            depends_on=[],
        )
    )

    tools.register(
        ToolDefinition(
            tool_id="browser",
            name="Browser tool",
            capability="browser",
            depends_on=["docker"],
        )
    )

    print(json.dumps({"status": "written"}))


def do_read() -> None:
    capabilities, providers, resources, tools = _registries()

    browser_tool = tools.get("browser")
    groq_provider = providers.get("groq")
    coding_providers = [p.provider_id for p in providers.find_by_capability("coding")]

    depends_on_map = {
        "browser": browser_tool.depends_on if browser_tool else [],
        "docker": [],
        "postgres": [],
    }
    resolution_order = resolve_dependencies("browser", depends_on_map)

    result = {
        "capability_count": len(capabilities.list_all()),
        "browser_tool_found": browser_tool is not None,
        "browser_tool_depends_on": browser_tool.depends_on if browser_tool else None,
        "groq_provider_found": groq_provider is not None,
        "groq_capabilities": groq_provider.capabilities if groq_provider else None,
        "coding_providers": coding_providers,
        "resource_count": len(resources.list_all()),
        "dependency_resolution_order": resolution_order,
    }
    print(json.dumps(result))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "write":
        do_write()
    elif mode == "read":
        do_read()
    else:
        raise SystemExit(f"Unknown mode: {mode}")

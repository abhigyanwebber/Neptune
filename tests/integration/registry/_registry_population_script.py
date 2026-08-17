"""Standalone script invoked as a SEPARATE OS process by
test_registry_population_recovery.py.

    python _registry_population_script.py load
        -> loads the real seed data from 06_REGISTRIES/data/*.yaml into
           Postgres-backed registries (with audit events wired), then this
           process exits (dies).
    python _registry_population_script.py verify
        -> a brand-new process reconnects, reads the catalog back,
           confirms the audit trail exists, exports a snapshot, and
           prints a summary as JSON.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

DATA_DIR = Path(__file__).resolve().parents[3] / "06_REGISTRIES" / "data"

from config.settings import get_database_url  # noqa: E402
from core.registry.audit import SYSTEM_REGISTRY_TASK_ID  # noqa: E402
from core.registry.capability_registry import CapabilityRegistry  # noqa: E402
from core.registry.provider_registry import ProviderRegistry  # noqa: E402
from core.registry.registry_exporter import export_registry_snapshot  # noqa: E402
from core.registry.registry_loader import load_registry_directory  # noqa: E402
from core.registry.resource_registry import ResourceRegistry  # noqa: E402
from core.registry.tool_registry import ToolRegistry  # noqa: E402
from infrastructure.persistence.database import (  # noqa: E402
    create_all_tables,
    make_engine,
    make_session_factory,
)
from infrastructure.persistence.repositories import (  # noqa: E402
    SqlAlchemyCapabilityRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyToolDefinitionRepository,
)


def _build(event_repo):
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return (
        CapabilityRegistry(SqlAlchemyCapabilityRepository(sf), event_repo=event_repo),
        ProviderRegistry(SqlAlchemyProviderRepository(sf), event_repo=event_repo),
        ResourceRegistry(SqlAlchemyResourceRepository(sf), event_repo=event_repo),
        ToolRegistry(SqlAlchemyToolDefinitionRepository(sf), event_repo=event_repo),
        SqlAlchemyEventRepository(sf),
    )


def do_load() -> None:
    events_placeholder = None
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)
    event_repo = SqlAlchemyEventRepository(sf)

    capabilities, providers, resources, tools, events = _build(event_repo)

    results = load_registry_directory(DATA_DIR, capabilities, providers, resources, tools)
    print(
        json.dumps(
            {
                "capabilities_loaded": results["capabilities"].total,
                "providers_loaded": results["providers"].total,
                "resources_loaded": results["resources"].total,
                "tools_loaded": results["tools"].total,
                "errors": (
                    results["capabilities"].errors
                    + results["providers"].errors
                    + results["resources"].errors
                    + results["tools"].errors
                ),
            }
        )
    )


def do_verify() -> None:
    capabilities, providers, resources, tools, events = _build(None)

    groq = providers.get("groq")
    ollama = providers.get("ollama")
    openai_compatible = providers.get("openai_compatible")

    audit_trail = events.list_for_task(SYSTEM_REGISTRY_TASK_ID)
    audit_event_types = {e.event_type for e in audit_trail}

    snapshot = export_registry_snapshot(capabilities, providers, resources, tools)

    result = {
        "provider_count": len(providers.list_all()),
        "groq_found": groq is not None,
        "groq_verification_status": groq.verification_status if groq else None,
        "ollama_found": ollama is not None,
        "openai_compatible_found": openai_compatible is not None,
        "audit_events_present": len(audit_trail) > 0,
        "audit_event_types_include_provider_registered": "registry.provider.registered"
        in audit_event_types,
        "snapshot_provider_count": len(snapshot["providers"]),
        "snapshot_schema_version": snapshot["schema_version"],
    }
    print(json.dumps(result))


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "load":
        do_load()
    elif mode == "verify":
        do_verify()
    else:
        raise SystemExit(f"Unknown mode: {mode}")

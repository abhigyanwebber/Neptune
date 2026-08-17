import json

import pytest
from sqlalchemy import create_engine

from core.registry.capability_registry import Capability, CapabilityRegistry
from core.registry.provider_registry import Provider, ProviderRegistry
from core.registry.registry_exporter import (
    SNAPSHOT_SCHEMA_VERSION,
    export_registry_snapshot,
    export_registry_snapshot_to_file,
)
from core.registry.resource_registry import Resource, ResourceRegistry
from core.registry.tool_registry import ToolDefinition, ToolRegistry
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyCapabilityRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyToolDefinitionRepository,
)


@pytest.fixture()
def populated_registries():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)

    capabilities = CapabilityRegistry(SqlAlchemyCapabilityRepository(sf))
    providers = ProviderRegistry(SqlAlchemyProviderRepository(sf))
    resources = ResourceRegistry(SqlAlchemyResourceRepository(sf))
    tools = ToolRegistry(SqlAlchemyToolDefinitionRepository(sf))

    capabilities.register(Capability(capability_id="coding", name="Coding"))
    providers.register(Provider(provider_id="groq", name="Groq", capabilities=["coding"]))
    resources.register(Resource(resource_id="docker", name="Docker", status="ACTIVE"))
    tools.register(ToolDefinition(tool_id="terminal", name="Terminal", capability="terminal"))

    return capabilities, providers, resources, tools


def test_export_snapshot_structure(populated_registries):
    snapshot = export_registry_snapshot(*populated_registries)

    assert snapshot["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert "exported_at" in snapshot
    assert [c["capability_id"] for c in snapshot["capabilities"]] == ["coding"]
    assert [p["provider_id"] for p in snapshot["providers"]] == ["groq"]
    assert [r["resource_id"] for r in snapshot["resources"]] == ["docker"]
    assert [t["tool_id"] for t in snapshot["tools"]] == ["terminal"]


def test_export_snapshot_is_json_serializable(populated_registries):
    snapshot = export_registry_snapshot(*populated_registries)
    # Must not raise -- everything in the snapshot has to be plain JSON types.
    serialized = json.dumps(snapshot)
    assert "groq" in serialized


def test_export_snapshot_to_file(tmp_path, populated_registries):
    out_path = tmp_path / "exports" / "snapshot.json"
    result_path = export_registry_snapshot_to_file(out_path, *populated_registries)

    assert result_path == out_path
    assert out_path.exists()

    loaded = json.loads(out_path.read_text())
    assert loaded["schema_version"] == SNAPSHOT_SCHEMA_VERSION
    assert loaded["providers"][0]["provider_id"] == "groq"


def test_export_empty_registries_produces_empty_lists():
    from sqlalchemy import create_engine as ce

    engine = ce("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)

    snapshot = export_registry_snapshot(
        CapabilityRegistry(SqlAlchemyCapabilityRepository(sf)),
        ProviderRegistry(SqlAlchemyProviderRepository(sf)),
        ResourceRegistry(SqlAlchemyResourceRepository(sf)),
        ToolRegistry(SqlAlchemyToolDefinitionRepository(sf)),
    )
    assert snapshot["capabilities"] == []
    assert snapshot["providers"] == []
    assert snapshot["resources"] == []
    assert snapshot["tools"] == []

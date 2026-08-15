import pytest
from sqlalchemy import create_engine

from core.registry.capability_registry import CapabilityRegistry
from core.registry.provider_registry import ProviderRegistry
from core.registry.registry_loader import (
    load_capabilities,
    load_providers,
    load_registry_directory,
    load_resources,
    load_tools,
)
from core.registry.resource_registry import ResourceRegistry
from core.registry.tool_registry import ToolRegistry
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyCapabilityRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyToolDefinitionRepository,
)

REPO_ROOT_DATA_DIR = __import__("pathlib").Path(__file__).resolve().parents[3] / "06_REGISTRIES" / "data"


@pytest.fixture()
def registries():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return (
        CapabilityRegistry(SqlAlchemyCapabilityRepository(sf)),
        ProviderRegistry(SqlAlchemyProviderRepository(sf)),
        ResourceRegistry(SqlAlchemyResourceRepository(sf)),
        ToolRegistry(SqlAlchemyToolDefinitionRepository(sf)),
    )


def test_load_providers_from_yaml(tmp_path, registries):
    _, provider_registry, _, _ = registries
    yaml_path = tmp_path / "providers.yaml"
    yaml_path.write_text(
        """
providers:
  - provider_id: groq
    name: Groq
    capabilities: [coding, reasoning]
    depends_on: []
"""
    )
    result = load_providers(yaml_path, provider_registry)
    assert result.registered == ["groq"]
    assert result.updated == []
    assert result.errors == []

    provider = provider_registry.get("groq")
    assert provider.name == "Groq"
    assert provider.capabilities == ["coding", "reasoning"]


def test_reloading_same_file_updates_instead_of_duplicating(tmp_path, registries):
    _, provider_registry, _, _ = registries
    yaml_path = tmp_path / "providers.yaml"
    yaml_path.write_text("providers:\n  - provider_id: groq\n    name: Groq\n")

    first = load_providers(yaml_path, provider_registry)
    assert first.registered == ["groq"]

    yaml_path.write_text("providers:\n  - provider_id: groq\n    name: Groq (renamed)\n")
    second = load_providers(yaml_path, provider_registry)
    assert second.registered == []
    assert second.updated == ["groq"]

    assert provider_registry.get("groq").name == "Groq (renamed)"
    assert len(provider_registry.list_all()) == 1


def test_load_rejects_unknown_vocabulary_and_continues(tmp_path, registries):
    _, provider_registry, _, _ = registries
    yaml_path = tmp_path / "providers.yaml"
    yaml_path.write_text(
        """
providers:
  - provider_id: totally-made-up
    name: Nope
  - provider_id: groq
    name: Groq
"""
    )
    result = load_providers(yaml_path, provider_registry)
    assert result.registered == ["groq"]
    assert len(result.errors) == 1
    assert "totally-made-up" in result.errors[0]


def test_load_missing_file_is_a_noop(tmp_path, registries):
    _, provider_registry, _, _ = registries
    result = load_providers(tmp_path / "does-not-exist.yaml", provider_registry)
    assert result.total == 0
    assert result.errors == []


def test_load_capabilities_resources_tools(tmp_path, registries):
    capability_registry, _, resource_registry, tool_registry = registries

    (tmp_path / "capabilities.yaml").write_text(
        "capabilities:\n  - capability_id: coding\n    name: Coding\n"
    )
    (tmp_path / "resources.yaml").write_text(
        "resources:\n  - resource_id: docker\n    name: Docker\n    status: ACTIVE\n"
    )
    (tmp_path / "tools.yaml").write_text(
        "tools:\n  - tool_id: terminal\n    name: Terminal\n    capability: terminal\n"
    )

    cap_result = load_capabilities(tmp_path / "capabilities.yaml", capability_registry)
    res_result = load_resources(tmp_path / "resources.yaml", resource_registry)
    tool_result = load_tools(tmp_path / "tools.yaml", tool_registry)

    assert cap_result.registered == ["coding"]
    assert res_result.registered == ["docker"]
    assert tool_result.registered == ["terminal"]


def test_load_registry_directory_loads_all_four(tmp_path, registries):
    capability_registry, provider_registry, resource_registry, tool_registry = registries

    (tmp_path / "capabilities.yaml").write_text(
        "capabilities:\n  - capability_id: coding\n    name: Coding\n"
    )
    (tmp_path / "providers.yaml").write_text("providers:\n  - provider_id: groq\n    name: Groq\n")
    (tmp_path / "resources.yaml").write_text(
        "resources:\n  - resource_id: docker\n    name: Docker\n"
    )
    (tmp_path / "tools.yaml").write_text(
        "tools:\n  - tool_id: terminal\n    name: Terminal\n    capability: terminal\n"
    )

    results = load_registry_directory(
        tmp_path, capability_registry, provider_registry, resource_registry, tool_registry
    )
    assert results["capabilities"].registered == ["coding"]
    assert results["providers"].registered == ["groq"]
    assert results["resources"].registered == ["docker"]
    assert results["tools"].registered == ["terminal"]


def test_load_real_seed_providers_yaml(registries):
    """The actual verified-facts seed data at 06_REGISTRIES/data/providers.yaml
    loads cleanly with no errors and produces all five entries the
    director asked for."""
    _, provider_registry, _, _ = registries
    result = load_providers(REPO_ROOT_DATA_DIR / "providers.yaml", provider_registry)
    assert result.errors == []
    assert set(result.registered) == {"groq", "openrouter", "gemini", "ollama", "openai_compatible"}

    groq = provider_registry.get("groq")
    assert groq.verification_status == "verified"
    assert "api.groq.com/openai/v1" in groq.notes

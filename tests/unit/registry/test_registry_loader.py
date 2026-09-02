import pytest
from sqlalchemy import create_engine

from core.registry.capability_registry import CapabilityRegistry
from core.registry.model_registry import ModelRegistry
from core.registry.provider_registry import ProviderRegistry
from core.registry.registry_loader import (
    load_capabilities,
    load_models,
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
    SqlAlchemyModelRepository,
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
        ModelRegistry(SqlAlchemyModelRepository(sf)),
    )


def test_load_providers_from_yaml(tmp_path, registries):
    _, provider_registry, _, _, _ = registries
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
    _, provider_registry, _, _, _ = registries
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
    _, provider_registry, _, _, _ = registries
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
    _, provider_registry, _, _, _ = registries
    result = load_providers(tmp_path / "does-not-exist.yaml", provider_registry)
    assert result.total == 0
    assert result.errors == []


def test_load_capabilities_resources_tools(tmp_path, registries):
    capability_registry, _, resource_registry, tool_registry, _ = registries

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


def test_load_models_from_yaml(tmp_path, registries):
    _, _, _, _, model_registry = registries
    yaml_path = tmp_path / "models.yaml"
    yaml_path.write_text(
        """
models:
  - model_id: groq-llama-3.3-70b-versatile
    provider_id: groq
    provider_model_name: llama-3.3-70b-versatile
    capabilities: [coding, tool_use]
"""
    )
    result = load_models(yaml_path, model_registry)
    assert result.registered == ["groq-llama-3.3-70b-versatile"]
    assert result.errors == []

    model = model_registry.get("groq-llama-3.3-70b-versatile")
    assert model.provider_id == "groq"
    assert model.provider_model_name == "llama-3.3-70b-versatile"


def test_load_registry_directory_loads_all_five(tmp_path, registries):
    capability_registry, provider_registry, resource_registry, tool_registry, model_registry = registries

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
    (tmp_path / "models.yaml").write_text(
        "models:\n  - model_id: m1\n    provider_id: groq\n    provider_model_name: x\n"
    )

    results = load_registry_directory(
        tmp_path,
        capability_registry,
        provider_registry,
        resource_registry,
        tool_registry,
        model_registry=model_registry,
    )
    assert results["capabilities"].registered == ["coding"]
    assert results["providers"].registered == ["groq"]
    assert results["resources"].registered == ["docker"]
    assert results["tools"].registered == ["terminal"]
    assert results["models"].registered == ["m1"]


def test_load_registry_directory_without_model_registry_still_works(tmp_path, registries):
    # Backward compatibility: existing A-004 callers that don't pass
    # model_registry must keep working unmodified (additive parameter).
    capability_registry, provider_registry, resource_registry, tool_registry, _ = registries

    (tmp_path / "providers.yaml").write_text("providers:\n  - provider_id: groq\n    name: Groq\n")

    results = load_registry_directory(
        tmp_path, capability_registry, provider_registry, resource_registry, tool_registry
    )
    assert "models" not in results
    assert results["providers"].registered == ["groq"]


def test_load_real_seed_providers_yaml(registries):
    """The actual verified-facts seed data at 06_REGISTRIES/data/providers.yaml
    loads cleanly with no errors and produces all five entries, now
    including the C-004 operational metadata migration on groq."""
    _, provider_registry, _, _, _ = registries
    result = load_providers(REPO_ROOT_DATA_DIR / "providers.yaml", provider_registry)
    assert result.errors == []
    assert set(result.registered) == {"groq", "openrouter", "gemini", "ollama", "openai_compatible"}

    groq = provider_registry.get("groq")
    assert groq.verification_status == "verified"
    assert "api.groq.com/openai/v1" in groq.notes
    assert groq.endpoints == ["https://api.groq.com/openai/v1"]
    assert groq.regions == ["us"]
    assert groq.terms_url == "https://groq.com/terms-of-use/"


def test_load_real_seed_models_yaml(registries):
    """The actual migrated model seed data at 06_REGISTRIES/data/models.yaml
    loads cleanly. model_id/provider_model_name updated during B-008's
    live validation: Groq's real API confirmed (live 404)
    "llama-3.3-70b-versatile" no longer exists; "openai/gpt-oss-120b"
    is the current, live-confirmed, tool-calling-capable replacement
    (see 06_REGISTRIES/data/models.yaml's own header comment and
    DEVELOPMENT_STATE/decisions.yaml for the B-008 entry)."""
    _, _, _, _, model_registry = registries
    result = load_models(REPO_ROOT_DATA_DIR / "models.yaml", model_registry)
    assert result.errors == []
    assert result.registered == ["groq-openai-gpt-oss-120b"]

    model = model_registry.get("groq-openai-gpt-oss-120b")
    assert model.provider_id == "groq"
    assert model.provider_model_name == "openai/gpt-oss-120b"
    assert model.status == "available"
    assert model.verification_status == "verified"
    # fast_general deliberately dropped per ADR-042 -- must not appear.
    assert "fast_general" not in model.capabilities
    assert set(model.capabilities) == {"tool_use", "coding", "summarization", "classification"}

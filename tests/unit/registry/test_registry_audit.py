import pytest
from sqlalchemy import create_engine

from core.registry.audit import SYSTEM_REGISTRY_TASK_ID
from core.registry.capability_registry import Capability, CapabilityRegistry
from core.registry.provider_registry import Provider, ProviderRegistry
from infrastructure.persistence.database import create_all_tables, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyCapabilityRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyProviderRepository,
)


@pytest.fixture()
def event_repo_and_session_factory():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    create_all_tables(engine)
    sf = make_session_factory(engine)
    return SqlAlchemyEventRepository(sf), sf


def test_registry_mutations_emit_events(event_repo_and_session_factory):
    events, sf = event_repo_and_session_factory
    registry = CapabilityRegistry(SqlAlchemyCapabilityRepository(sf), event_repo=events)

    registry.register(Capability(capability_id="coding", name="Coding"))
    cap = registry.get("coding")
    cap.name = "Software Coding"
    registry.update(cap)
    registry.delete("coding")

    audit_trail = events.list_for_task(SYSTEM_REGISTRY_TASK_ID)
    event_types = [e.event_type for e in audit_trail]
    assert event_types == [
        "registry.capability.registered",
        "registry.capability.updated",
        "registry.capability.deleted",
    ]
    assert all(e.actor == "core-registry" for e in audit_trail)
    assert all(e.payload["entity_id"] == "coding" for e in audit_trail)


def test_registry_without_event_repo_does_not_emit(event_repo_and_session_factory):
    events, sf = event_repo_and_session_factory
    # No event_repo passed -- registries must remain fully usable without one.
    registry = CapabilityRegistry(SqlAlchemyCapabilityRepository(sf))
    registry.register(Capability(capability_id="coding", name="Coding"))

    assert events.list_for_task(SYSTEM_REGISTRY_TASK_ID) == []
    assert registry.get("coding") is not None


def test_multiple_registries_share_the_same_audit_trail(event_repo_and_session_factory):
    events, sf = event_repo_and_session_factory
    capability_registry = CapabilityRegistry(SqlAlchemyCapabilityRepository(sf), event_repo=events)
    provider_registry = ProviderRegistry(SqlAlchemyProviderRepository(sf), event_repo=events)

    capability_registry.register(Capability(capability_id="coding", name="Coding"))
    provider_registry.register(Provider(provider_id="groq", name="Groq", capabilities=["coding"]))

    audit_trail = events.list_for_task(SYSTEM_REGISTRY_TASK_ID)
    event_types = {e.event_type for e in audit_trail}
    assert event_types == {"registry.capability.registered", "registry.provider.registered"}

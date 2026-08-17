"""SQLAlchemy implementations of the registry repository contracts.

Same one-transaction-per-call pattern as
infrastructure/persistence/repositories/sqlalchemy_repositories.py
(ADR-A-002). Only this module imports SQLAlchemy for the registry side;
core/registry and core/contracts/registry.py stay persistence-agnostic.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as SqlAlchemySession
from sqlalchemy.orm import sessionmaker

from core.registry.capability_registry import Capability
from core.registry.provider_registry import Provider
from core.registry.resource_registry import Resource
from core.registry.tool_registry import ToolDefinition

from ..models.orm import (
    CapabilityModel,
    ProviderModel,
    ResourceModel,
    ToolDefinitionModel,
)


class SqlAlchemyCapabilityRepository:
    def __init__(self, session_factory: sessionmaker[SqlAlchemySession]) -> None:
        self._session_factory = session_factory

    def create(self, capability: Capability) -> None:
        with self._session_factory() as db:
            db.add(_capability_to_model(capability))
            db.commit()

    def get(self, capability_id: str) -> Optional[Capability]:
        with self._session_factory() as db:
            model = db.get(CapabilityModel, capability_id)
            return _model_to_capability(model) if model else None

    def update(self, capability: Capability) -> None:
        with self._session_factory() as db:
            model = db.get(CapabilityModel, capability.capability_id)
            if model is None:
                raise ValueError(f"Capability not found: {capability.capability_id}")
            model.name = capability.name
            model.description = capability.description
            model.verification_date = capability.verification_date
            model.verification_source = capability.verification_source
            model.verification_status = capability.verification_status
            model.last_checked = capability.last_checked
            db.commit()

    def delete(self, capability_id: str) -> None:
        with self._session_factory() as db:
            model = db.get(CapabilityModel, capability_id)
            if model is not None:
                db.delete(model)
                db.commit()

    def list_all(self) -> list[Capability]:
        with self._session_factory() as db:
            return [_model_to_capability(m) for m in db.scalars(select(CapabilityModel))]


class SqlAlchemyProviderRepository:
    def __init__(self, session_factory: sessionmaker[SqlAlchemySession]) -> None:
        self._session_factory = session_factory

    def create(self, provider: Provider) -> None:
        with self._session_factory() as db:
            db.add(_provider_to_model(provider))
            db.commit()

    def get(self, provider_id: str) -> Optional[Provider]:
        with self._session_factory() as db:
            model = db.get(ProviderModel, provider_id)
            return _model_to_provider(model) if model else None

    def update(self, provider: Provider) -> None:
        with self._session_factory() as db:
            model = db.get(ProviderModel, provider.provider_id)
            if model is None:
                raise ValueError(f"Provider not found: {provider.provider_id}")
            _apply_provider_to_model(provider, model)
            db.commit()

    def delete(self, provider_id: str) -> None:
        with self._session_factory() as db:
            model = db.get(ProviderModel, provider_id)
            if model is not None:
                db.delete(model)
                db.commit()

    def list_all(self) -> list[Provider]:
        with self._session_factory() as db:
            return [_model_to_provider(m) for m in db.scalars(select(ProviderModel))]


class SqlAlchemyResourceRepository:
    def __init__(self, session_factory: sessionmaker[SqlAlchemySession]) -> None:
        self._session_factory = session_factory

    def create(self, resource: Resource) -> None:
        with self._session_factory() as db:
            db.add(_resource_to_model(resource))
            db.commit()

    def get(self, resource_id: str) -> Optional[Resource]:
        with self._session_factory() as db:
            model = db.get(ResourceModel, resource_id)
            return _model_to_resource(model) if model else None

    def update(self, resource: Resource) -> None:
        with self._session_factory() as db:
            model = db.get(ResourceModel, resource.resource_id)
            if model is None:
                raise ValueError(f"Resource not found: {resource.resource_id}")
            _apply_resource_to_model(resource, model)
            db.commit()

    def delete(self, resource_id: str) -> None:
        with self._session_factory() as db:
            model = db.get(ResourceModel, resource_id)
            if model is not None:
                db.delete(model)
                db.commit()

    def list_all(self) -> list[Resource]:
        with self._session_factory() as db:
            return [_model_to_resource(m) for m in db.scalars(select(ResourceModel))]


class SqlAlchemyToolDefinitionRepository:
    def __init__(self, session_factory: sessionmaker[SqlAlchemySession]) -> None:
        self._session_factory = session_factory

    def create(self, tool: ToolDefinition) -> None:
        with self._session_factory() as db:
            db.add(_tool_to_model(tool))
            db.commit()

    def get(self, tool_id: str) -> Optional[ToolDefinition]:
        with self._session_factory() as db:
            model = db.get(ToolDefinitionModel, tool_id)
            return _model_to_tool(model) if model else None

    def update(self, tool: ToolDefinition) -> None:
        with self._session_factory() as db:
            model = db.get(ToolDefinitionModel, tool.tool_id)
            if model is None:
                raise ValueError(f"Tool not found: {tool.tool_id}")
            _apply_tool_to_model(tool, model)
            db.commit()

    def delete(self, tool_id: str) -> None:
        with self._session_factory() as db:
            model = db.get(ToolDefinitionModel, tool_id)
            if model is not None:
                db.delete(model)
                db.commit()

    def list_all(self) -> list[ToolDefinition]:
        with self._session_factory() as db:
            return [_model_to_tool(m) for m in db.scalars(select(ToolDefinitionModel))]


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------

def _capability_to_model(c: Capability) -> CapabilityModel:
    return CapabilityModel(
        capability_id=c.capability_id,
        name=c.name,
        description=c.description,
        verification_date=c.verification_date,
        verification_source=c.verification_source,
        verification_status=c.verification_status,
        last_checked=c.last_checked,
    )


def _model_to_capability(m: CapabilityModel) -> Capability:
    return Capability(
        capability_id=m.capability_id,
        name=m.name,
        description=m.description,
        verification_date=m.verification_date,
        verification_source=m.verification_source,
        verification_status=m.verification_status,
        last_checked=m.last_checked,
    )


def _provider_to_model(p: Provider) -> ProviderModel:
    return ProviderModel(
        provider_id=p.provider_id,
        name=p.name,
        provider_type=p.provider_type,
        capabilities=p.capabilities,
        status=p.status,
        depends_on=p.depends_on,
        verification_date=p.verification_date,
        notes=p.notes,
        verification_source=p.verification_source,
        verification_status=p.verification_status,
        last_checked=p.last_checked,
    )


def _apply_provider_to_model(p: Provider, m: ProviderModel) -> None:
    m.name = p.name
    m.provider_type = p.provider_type
    m.capabilities = p.capabilities
    m.status = p.status
    m.depends_on = p.depends_on
    m.verification_date = p.verification_date
    m.notes = p.notes
    m.verification_source = p.verification_source
    m.verification_status = p.verification_status
    m.last_checked = p.last_checked


def _model_to_provider(m: ProviderModel) -> Provider:
    return Provider(
        provider_id=m.provider_id,
        name=m.name,
        provider_type=m.provider_type,
        capabilities=list(m.capabilities or []),
        status=m.status,
        depends_on=list(m.depends_on or []),
        verification_date=m.verification_date,
        notes=m.notes,
        verification_source=m.verification_source,
        verification_status=m.verification_status,
        last_checked=m.last_checked,
    )


def _resource_to_model(r: Resource) -> ResourceModel:
    return ResourceModel(
        resource_id=r.resource_id,
        name=r.name,
        resource_type=r.resource_type,
        status=r.status,
        criticality=r.criticality,
        depends_on=r.depends_on,
        verification_date=r.verification_date,
        notes=r.notes,
        verification_source=r.verification_source,
        verification_status=r.verification_status,
        last_checked=r.last_checked,
    )


def _apply_resource_to_model(r: Resource, m: ResourceModel) -> None:
    m.name = r.name
    m.resource_type = r.resource_type
    m.status = r.status
    m.criticality = r.criticality
    m.depends_on = r.depends_on
    m.verification_date = r.verification_date
    m.notes = r.notes
    m.verification_source = r.verification_source
    m.verification_status = r.verification_status
    m.last_checked = r.last_checked


def _model_to_resource(m: ResourceModel) -> Resource:
    return Resource(
        resource_id=m.resource_id,
        name=m.name,
        resource_type=m.resource_type,
        status=m.status,
        criticality=m.criticality,
        depends_on=list(m.depends_on or []),
        verification_date=m.verification_date,
        notes=m.notes,
        verification_source=m.verification_source,
        verification_status=m.verification_status,
        last_checked=m.last_checked,
    )


def _tool_to_model(t: ToolDefinition) -> ToolDefinitionModel:
    return ToolDefinitionModel(
        tool_id=t.tool_id,
        name=t.name,
        capability=t.capability,
        risk_class=t.risk_class,
        depends_on=t.depends_on,
        verification_date=t.verification_date,
        notes=t.notes,
        verification_source=t.verification_source,
        verification_status=t.verification_status,
        last_checked=t.last_checked,
    )


def _apply_tool_to_model(t: ToolDefinition, m: ToolDefinitionModel) -> None:
    m.name = t.name
    m.capability = t.capability
    m.risk_class = t.risk_class
    m.depends_on = t.depends_on
    m.verification_date = t.verification_date
    m.notes = t.notes
    m.verification_source = t.verification_source
    m.verification_status = t.verification_status
    m.last_checked = t.last_checked


def _model_to_tool(m: ToolDefinitionModel) -> ToolDefinition:
    return ToolDefinition(
        tool_id=m.tool_id,
        name=m.name,
        capability=m.capability,
        risk_class=m.risk_class,
        depends_on=list(m.depends_on or []),
        verification_date=m.verification_date,
        notes=m.notes,
        verification_source=m.verification_source,
        verification_status=m.verification_status,
        last_checked=m.last_checked,
    )

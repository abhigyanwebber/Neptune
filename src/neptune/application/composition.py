"""Composition root for the Neptune MVP path (T1).

Assembles the EXISTING components into one runnable PlanRunner -- it adds
no new registry, runtime, executor, permission system, or context
mechanism, and does not bypass RuntimeDriver:

    GoalPlanner -> PlanRunner -> RuntimeDriver (context_provider =
    ToolOfferingResolver) -> ModelGatewayAdapter -> ToolPortAdapter ->
    ToolExecutorService (DefaultPermissionPolicy + ApprovalProvider) ->
    real filesystem/shell tools

This module is the only place that knows how those pieces fit together
outside tests. Core (`src/core`) stays independent of everything here:
PlanRunner receives a `driver_factory` closure built below.

Model seam: `model_gateway_factory(task_id, session_id, concrete_tools)`
returns a ModelGatewayPort. The default builds the real Groq-backed
ModelGatewayAdapter; a test may supply a fake. Nothing else is faked in
the CLI integration test.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Callable, Optional

from config.settings import get_database_url
from core.planning.executor import PlanExecutor
from core.planning.plan_runner import PlanRunner
from core.planning.planner import GoalPlanner
from core.registry.capability_registry import CapabilityRegistry
from core.registry.model_registry import ModelRegistry as CanonicalModelRegistry
from core.registry.provider_registry import ProviderRegistry
from core.registry.registry_loader import load_registry_directory
from core.registry.resource_registry import ResourceRegistry
from core.registry.tool_registry import ToolRegistry as CanonicalToolRegistry
from core.resolution.capability_resolver import CapabilityResolver
from core.resolution.provider_resolver import ProviderResolver
from core.resolution.resource_resolver import ResourceResolver
from core.resolution.tool_offering_resolver import ToolOfferingResolver
from core.runtime.driver import DriverConfig, RuntimeDriver
from core.runtime.engine import AgentRuntime
from infrastructure.persistence.database import create_all_tables, make_engine, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyAgentRepository,
    SqlAlchemyCapabilityRepository,
    SqlAlchemyCheckpointRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyModelRepository,
    SqlAlchemyPlanRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyToolDefinitionRepository,
    SqlAlchemyTurnRepository,
)
from neptune.infrastructure.security.approval import ApprovalProvider
from neptune.infrastructure.tools.executor import ToolExecutorService
from neptune.infrastructure.tools.filesystem_tools import ListDirectoryTool, ReadFileTool, WriteFileTool
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter
from neptune.infrastructure.tools.shell_tool import RunCommandTool
from neptune.infrastructure.tools.tool_port_adapter import ToolPortAdapter
from neptune.infrastructure.tools.workspace_boundary import WorkspaceBoundary

# Canonical capabilities whose tools are offered to the model: filesystem
# is catalogued under "tool_use", the shell under "terminal"
# (06_REGISTRIES/data/tools.yaml). Other catalog entries (browser, mcp,
# search) have no real backing and are not requested.
OFFERED_CAPABILITIES = ["tool_use", "terminal"]

DEFAULT_REGISTRY_DIR = Path(__file__).resolve().parents[3] / "06_REGISTRIES" / "data"
DEFAULT_MAX_TURNS_PER_STEP = 12

ModelGatewayFactory = Callable[[str, str, list], Any]


def _default_model_gateway_factory(session_factory) -> ModelGatewayFactory:
    """Real Groq-backed gateway (B-008). Imported lazily so composing with
    an injected model never requires provider code or credentials."""
    from neptune.application.gateway_service import ModelGatewayService
    from neptune.infrastructure.gateway.model_gateway_adapter import ModelGatewayAdapter
    from neptune.infrastructure.models.canonical_registry_adapter import CanonicalRegistryCandidateSource
    from neptune.infrastructure.providers.groq_adapter import GroqAdapter
    from neptune.infrastructure.routing.capability_router import CapabilityRouter

    cap_reg = CapabilityRegistry(SqlAlchemyCapabilityRepository(session_factory))
    prov_reg = ProviderRegistry(SqlAlchemyProviderRepository(session_factory))
    res_reg = ResourceRegistry(SqlAlchemyResourceRepository(session_factory))
    tool_reg = CanonicalToolRegistry(SqlAlchemyToolDefinitionRepository(session_factory))
    model_reg = CanonicalModelRegistry(SqlAlchemyModelRepository(session_factory))
    prov_resolver = ProviderResolver(
        CapabilityResolver(cap_reg, prov_reg, tool_reg),
        ResourceResolver(cap_reg, prov_reg, res_reg, tool_reg),
        prov_reg,
    )
    gateway_service = ModelGatewayService(
        registry=CanonicalRegistryCandidateSource(prov_resolver, model_reg),
        router=CapabilityRouter(),
        adapters={"groq": GroqAdapter()},
    )

    def factory(task_id: str, session_id: str, concrete_tools: list):
        return ModelGatewayAdapter(
            gateway_service,
            task_id=task_id,
            session_id=session_id,
            concrete_tool_definitions=concrete_tools,
        )

    return factory


def build_plan_runner(
    *,
    workspace: Path,
    approval_provider: ApprovalProvider,
    registry_dir: Path = DEFAULT_REGISTRY_DIR,
    session_factory=None,
    model_gateway_factory: Optional[ModelGatewayFactory] = None,
    max_turns_per_step: int = DEFAULT_MAX_TURNS_PER_STEP,
) -> PlanRunner:
    if session_factory is None:
        engine = make_engine(get_database_url())
        create_all_tables(engine)
        session_factory = make_session_factory(engine)
    sf = session_factory

    # Seed the canonical catalog (idempotent upsert of the shipped YAML).
    tool_registry = CanonicalToolRegistry(SqlAlchemyToolDefinitionRepository(sf))
    results = load_registry_directory(
        registry_dir,
        CapabilityRegistry(SqlAlchemyCapabilityRepository(sf)),
        ProviderRegistry(SqlAlchemyProviderRepository(sf)),
        ResourceRegistry(SqlAlchemyResourceRepository(sf)),
        tool_registry,
        CanonicalModelRegistry(SqlAlchemyModelRepository(sf)),
    )
    load_errors = {name: r.errors for name, r in results.items() if r.errors}
    if load_errors:
        raise RuntimeError(f"registry seed data failed to load: {load_errors}")

    # Real tools, all confined to one workspace. ToolExecutorService keeps
    # its secure-by-default DefaultPermissionPolicy (nothing overridden);
    # ASK verdicts go to the supplied approval provider.
    boundary = WorkspaceBoundary(workspace)
    tools = [
        ReadFileTool(boundary),
        WriteFileTool(boundary),
        ListDirectoryTool(boundary),
        RunCommandTool(boundary.root),
    ]
    concrete_tools = [t.definition() for t in tools]
    executor = ToolExecutorService(ToolRegistryAdapter(tools), approval_provider=approval_provider)

    resolver = ToolOfferingResolver(tool_registry)

    def context_provider() -> dict:
        return {"available_tools": resolver.available_tools(capability_ids=OFFERED_CAPABILITIES)}

    factory = model_gateway_factory or _default_model_gateway_factory(sf)

    def driver_factory(task_id: str) -> RuntimeDriver:
        session_hint = f"{task_id}-session"
        runtime = AgentRuntime(
            task_repo=SqlAlchemyTaskRepository(sf),
            agent_repo=SqlAlchemyAgentRepository(sf),
            session_repo=SqlAlchemySessionRepository(sf),
            turn_repo=SqlAlchemyTurnRepository(sf),
            event_repo=SqlAlchemyEventRepository(sf),
            checkpoint_repo=SqlAlchemyCheckpointRepository(sf),
            model_gateway=factory(task_id, session_hint, concrete_tools),
            tool_port=ToolPortAdapter(executor, task_id=task_id, session_id=session_hint),
        )
        return RuntimeDriver(
            runtime,
            config=DriverConfig(max_turns=max_turns_per_step),
            context_provider=context_provider,
        )

    plan_repository = SqlAlchemyPlanRepository(sf)
    plan_executor = PlanExecutor(plan_repository)
    planning_id = f"planning-{uuid.uuid4().hex[:8]}"
    planner = GoalPlanner(
        model_gateway=factory(planning_id, f"{planning_id}-session", []),
        plan_repository=plan_repository,
        plan_executor=plan_executor,
    )
    return PlanRunner(planner=planner, executor=plan_executor, driver_factory=driver_factory)

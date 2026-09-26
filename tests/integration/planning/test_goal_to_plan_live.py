"""Real Goal -> Plan generation with a real Groq model (A-010).

Requires GROQ_API_KEY and live Postgres. Skips cleanly otherwise -- same
honest-skip convention as tests/integration/runtime/test_full_live_agent_loop.py
(B-009): never claim this is proven without the live credential.

Proves: real goal -> real ModelGatewayPort.send() reaching real Groq ->
structured plan content -> a valid core.planning.models.Plan -> persisted
via the real SqlAlchemyPlanRepository. Execution (PlanExecutor driving the
steps) is not required by this task's success criteria and is not
attempted here -- see A-010 brief section 6.
"""
from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from config.settings import get_database_url
from core.planning.errors import PlanValidationError
from core.planning.executor import PlanExecutor
from core.planning.models import Goal
from infrastructure.persistence.database import create_all_tables, make_engine, make_session_factory
from infrastructure.persistence.repositories import SqlAlchemyPlanRepository

from core.planning.planner import GoalPlanner
from neptune.application.gateway_service import ModelGatewayService
from neptune.infrastructure.gateway.model_gateway_adapter import ModelGatewayAdapter
from neptune.infrastructure.models.canonical_registry_adapter import (
    CanonicalRegistryCandidateSource,
)
from neptune.infrastructure.providers.groq_adapter import GroqAdapter
from neptune.infrastructure.routing.capability_router import CapabilityRouter
from core.registry.capability_registry import CapabilityRegistry
from core.registry.model_registry import ModelRegistry as CanonicalModelRegistry
from core.registry.provider_registry import ProviderRegistry
from core.registry.resource_registry import ResourceRegistry
from core.registry.tool_registry import ToolRegistry
from core.resolution.capability_resolver import CapabilityResolver
from core.resolution.provider_resolver import ProviderResolver
from core.resolution.resource_resolver import ResourceResolver
from infrastructure.persistence.repositories import (
    SqlAlchemyCapabilityRepository,
    SqlAlchemyModelRepository,
    SqlAlchemyProviderRepository,
    SqlAlchemyResourceRepository,
    SqlAlchemyToolDefinitionRepository,
)

requires_live_groq_key = pytest.mark.skipif(
    not os.environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set -- live goal-to-plan test skipped, per A-010's "
    "instruction to skip honestly rather than claim live proof without it",
)


def _postgres_available() -> bool:
    try:
        engine = make_engine(get_database_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


requires_postgres = pytest.mark.skipif(
    not _postgres_available(),
    reason="Postgres not reachable at NEPTUNE_DATABASE_URL; run `docker compose up -d`",
)


@requires_postgres
@requires_live_groq_key
def test_real_goal_becomes_a_real_persisted_plan_via_real_groq() -> None:
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)

    cap_reg = CapabilityRegistry(SqlAlchemyCapabilityRepository(sf))
    prov_reg = ProviderRegistry(SqlAlchemyProviderRepository(sf))
    res_reg = ResourceRegistry(SqlAlchemyResourceRepository(sf))
    tool_reg = ToolRegistry(SqlAlchemyToolDefinitionRepository(sf))
    model_reg = CanonicalModelRegistry(SqlAlchemyModelRepository(sf))
    cap_resolver = CapabilityResolver(cap_reg, prov_reg, tool_reg)
    res_resolver = ResourceResolver(cap_reg, prov_reg, res_reg, tool_reg)
    prov_resolver = ProviderResolver(cap_resolver, res_resolver, prov_reg)
    candidate_source = CanonicalRegistryCandidateSource(prov_resolver, model_reg)

    goal_id = f"a010-live-{uuid.uuid4().hex[:8]}"
    session_id_hint = f"{goal_id}-session"

    gateway_service = ModelGatewayService(
        registry=candidate_source,
        router=CapabilityRouter(),
        adapters={"groq": GroqAdapter()},
    )
    # No tool_definitions -- the planner does not use tool-calling (see
    # planner.py module docstring); it asks for plain JSON content.
    model_gateway = ModelGatewayAdapter(gateway_service, task_id=goal_id, session_id=session_id_hint)

    plan_repository = SqlAlchemyPlanRepository(sf)
    executor = PlanExecutor(plan_repository)
    planner = GoalPlanner(model_gateway=model_gateway, plan_repository=plan_repository, plan_executor=executor)

    goal = Goal(
        goal_id=goal_id,
        description=(
            'Create a file named hello.txt containing "hello", '
            "then read it and verify its contents."
        ),
    )

    try:
        plan = planner.plan_goal(goal)
    except PlanValidationError as exc:
        pytest.fail(
            f"Real Groq model produced a plan that failed validation -- this is real-model "
            f"behavior variance, not necessarily an architectural failure (see A-009's live "
            f"test's precedent for documenting variance rather than hiding it): {exc}"
        )

    # --- Real model produced structured plan content ---
    assert len(plan.steps) >= 1
    for step in plan.steps:
        assert step.step_id
        assert step.title

    # --- Persisted via the real repository ---
    persisted = plan_repository.get(plan.plan_id)
    assert persisted is not None
    assert persisted.plan_id == plan.plan_id
    assert [s.step_id for s in persisted.steps] == [s.step_id for s in plan.steps]

    # --- PlanExecutor can consume it (success criterion 4) ---
    next_step = executor.select_next_step(persisted)
    assert next_step is not None  # at least the first, dependency-free step is executable

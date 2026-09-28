"""Goal -> Plan -> real execution (A-011).

The actual seam DIRECTOR_REVIEW_005.md found missing: GoalPlanner's
output reaching AgentRuntime/RuntimeDriver through the real, unmodified
execution architecture -- real ToolOfferingResolver (A-008) reading
the real canonical catalog, real ToolExecutorService with its real,
default-on DefaultPermissionPolicy (B-012), real filesystem/shell
tools (B-010), real Postgres persistence. Only the model itself is
replaced with FakeModelGateway (the same "fake model, real everything
else" composition B-011's own test file already established and this
file's driver_factory helper is deliberately modeled on).

No second runtime, executor, tool registry, or permission system is
built here -- PlanRunner (core/planning/plan_runner.py) is exercised
exactly as any other caller would use it: given a driver_factory
closure, it never constructs any of the above itself.
"""
from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from config.settings import get_database_url
from core.planning.executor import PlanExecutor
from core.planning.models import Goal, StepStatus
from core.planning.plan_runner import PlanRunner
from core.planning.planner import GoalPlanner
from core.registry.registry_loader import load_tools
from core.registry.tool_registry import ToolRegistry as CanonicalToolRegistry
from core.resolution.tool_offering_resolver import ToolOfferingResolver
from core.runtime.driver import DriverConfig, DriverOutcome, RuntimeDriver
from core.runtime.engine import AgentRuntime
from core.runtime.fakes import FakeModelGateway
from infrastructure.persistence.database import create_all_tables, make_engine, make_session_factory
from infrastructure.persistence.repositories import (
    SqlAlchemyAgentRepository,
    SqlAlchemyCheckpointRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyPlanRepository,
    SqlAlchemySessionRepository,
    SqlAlchemyTaskRepository,
    SqlAlchemyToolDefinitionRepository,
    SqlAlchemyTurnRepository,
)

from neptune.infrastructure.tools.executor import ToolExecutorService
from neptune.infrastructure.tools.filesystem_tools import ReadFileTool, WriteFileTool
from neptune.infrastructure.tools.registry_adapter import ToolRegistryAdapter
from neptune.infrastructure.tools.shell_tool import RunCommandTool
from neptune.infrastructure.tools.tool_port_adapter import ToolPortAdapter
from neptune.infrastructure.tools.workspace_boundary import WorkspaceBoundary


def _postgres_available() -> bool:
    try:
        engine = make_engine(get_database_url())
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except OperationalError:
        return False


pytestmark = pytest.mark.skipif(
    not _postgres_available(),
    reason="Postgres not reachable at NEPTUNE_DATABASE_URL; run `docker compose up -d`",
)


def _plan_content(steps: list[dict]) -> dict:
    return {"content": json.dumps({"steps": steps}), "tool_calls": []}


def _make_harness(sf, tmp_path: Path):
    """Real canonical catalog, real dynamic offering resolver, real
    filesystem+shell tools under one WorkspaceBoundary, real
    ToolExecutorService with its real default permission policy
    (nothing overridden) -- the same composition B-011/A-009's own
    tests already proved, reused unmodified."""
    canonical_tool_registry = CanonicalToolRegistry(SqlAlchemyToolDefinitionRepository(sf))
    load_result = load_tools(Path("06_REGISTRIES/data/tools.yaml"), canonical_tool_registry)
    assert load_result.errors == []
    resolver = ToolOfferingResolver(canonical_tool_registry)

    boundary = WorkspaceBoundary(tmp_path)
    real_tools = [ReadFileTool(boundary), WriteFileTool(boundary), RunCommandTool(boundary.root)]
    # No permission_policy override -- proves the SAME secure-by-default
    # DefaultPermissionPolicy B-012 wires in is the one PlanRunner's
    # steps actually run under, not a test-only bypass.
    real_executor = ToolExecutorService(ToolRegistryAdapter(real_tools))

    return resolver, real_executor


def _driver_factory(gateway, sf, resolver, real_executor, max_turns=4):
    def build(task_id: str) -> RuntimeDriver:
        session_id_hint = f"{task_id}-session"
        tool_port = ToolPortAdapter(real_executor, task_id=task_id, session_id=session_id_hint)
        runtime = AgentRuntime(
            task_repo=SqlAlchemyTaskRepository(sf),
            agent_repo=SqlAlchemyAgentRepository(sf),
            session_repo=SqlAlchemySessionRepository(sf),
            turn_repo=SqlAlchemyTurnRepository(sf),
            event_repo=SqlAlchemyEventRepository(sf),
            checkpoint_repo=SqlAlchemyCheckpointRepository(sf),
            model_gateway=gateway,
            tool_port=tool_port,
        )

        def context_provider() -> dict:
            return {"available_tools": resolver.available_tools(capability_ids=["tool_use"])}

        return RuntimeDriver(runtime, config=DriverConfig(max_turns=max_turns), context_provider=context_provider)

    return build


def test_real_goal_flows_through_plan_runner_to_real_execution(tmp_path: Path) -> None:
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)

    resolver, real_executor = _make_harness(sf, tmp_path)

    plan_repo = SqlAlchemyPlanRepository(sf)
    plan_executor = PlanExecutor(plan_repo)

    goal_id = f"a011-goal-{uuid.uuid4().hex[:8]}"
    gateway = FakeModelGateway(
        scripted_responses=[
            # 1. GoalPlanner's own model call -- structured plan JSON.
            _plan_content(
                [
                    {"step_id": "write", "title": "Write hello.txt"},
                    {"step_id": "read", "title": "Read hello.txt", "dependencies": ["write"]},
                ]
            ),
            # 2. Step "write", turn 1: real write_file tool call.
            {
                "content": "writing",
                "tool_calls": [{"tool_name": "write_file", "args": {"path": "hello.txt", "content": "hello"}}],
            },
            # 3. Step "write", turn 2: model is done.
            {"content": "wrote hello.txt", "tool_calls": []},
            # 4. Step "read", turn 1: real read_file tool call.
            {"content": "reading", "tool_calls": [{"tool_name": "read_file", "args": {"path": "hello.txt"}}]},
            # 5. Step "read", turn 2: model is done.
            {"content": "read back: hello", "tool_calls": []},
        ]
    )

    planner = GoalPlanner(model_gateway=gateway, plan_repository=plan_repo, plan_executor=plan_executor)
    runner = PlanRunner(
        planner=planner,
        executor=plan_executor,
        driver_factory=_driver_factory(gateway, sf, resolver, real_executor),
    )

    result = runner.run_goal(
        Goal(goal_id=goal_id, description="Write hello.txt containing hello, then read it back")
    )

    # --- 1: GoalPlanner's output IS the Plan that actually ran ---
    assert [s.step_id for s in result.plan.steps] == ["write", "read"]

    # --- 2/3: real, not mocked -- the file genuinely exists on disk ---
    real_file = tmp_path / "hello.txt"
    assert real_file.exists()
    assert real_file.read_text() == "hello"

    # --- 4: PlanExecutor and RuntimeDriver actually composed -- every
    #     step ran as a real RuntimeDriver.execute_task() call and its
    #     real outcome drove PlanExecutor's real transition methods ---
    assert [r.step_id for r in result.step_results] == ["write", "read"]
    assert all(r.driver_result.outcome == DriverOutcome.COMPLETED for r in result.step_results)
    assert result.plan.get_step("write").status == StepStatus.COMPLETED
    assert result.plan.get_step("read").status == StepStatus.COMPLETED
    assert plan_executor.all_succeeded(result.plan) is True

    # --- Dynamic tool offering was real request-time data, not skipped ---
    write_turn = result.step_results[0].driver_result.turns_run[0]
    assert write_turn.model_request["available_tools"][0]["tool_id"] == "filesystem"

    # --- 7/8: observation/continuation and completion/checkpoint semantics ---
    for r in result.step_results:
        assert r.driver_result.task is not None
        assert r.driver_result.task.status.value == "completed"
        assert r.driver_result.last_checkpoint is not None

    # --- Plan persisted in its final, real terminal state ---
    persisted = plan_repo.get(result.plan.plan_id)
    assert persisted.get_step("write").status == StepStatus.COMPLETED
    assert persisted.get_step("read").status == StepStatus.COMPLETED


def test_permission_denial_blocks_step_before_the_shell_never_runs(tmp_path: Path) -> None:
    """The real DefaultPermissionPolicy (B-012), not a test double,
    denies a real ToolCall before RunCommandTool.execute() ever runs --
    proven the same way B-012's own test proves it: a marker file the
    command would create if it ran. The resulting step must end FAILED,
    never COMPLETED, and any dependent step must cascade to SKIPPED
    (PlanExecutor's existing, unmodified behavior)."""
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)

    resolver, real_executor = _make_harness(sf, tmp_path)
    marker = tmp_path / "marker.txt"

    plan_repo = SqlAlchemyPlanRepository(sf)
    plan_executor = PlanExecutor(plan_repo)

    goal_id = f"a011-denied-{uuid.uuid4().hex[:8]}"
    gateway = FakeModelGateway(
        scripted_responses=[
            _plan_content(
                [
                    {"step_id": "dangerous", "title": "Delete the remote branch"},
                    {"step_id": "after", "title": "Do something after", "dependencies": ["dangerous"]},
                ]
            ),
            # The denied call: same deny-classified pattern B-012's own
            # unit/integration tests use, plus a marker-file side effect
            # that must never appear if the denial is real.
            {
                "content": "deleting",
                "tool_calls": [
                    {
                        "tool_name": "run_command",
                        "args": {"command": f"git push origin --delete x; echo ran > {marker}"},
                    }
                ],
            },
        ]
    )

    planner = GoalPlanner(model_gateway=gateway, plan_repository=plan_repo, plan_executor=plan_executor)
    runner = PlanRunner(
        planner=planner,
        executor=plan_executor,
        driver_factory=_driver_factory(gateway, sf, resolver, real_executor),
    )

    result = runner.run_goal(Goal(goal_id=goal_id, description="Delete a remote branch, then do more"))

    # --- Denied before execution: the shell command never ran ---
    assert not marker.exists(), "a denied command must never reach the shell"

    # --- Denial is a real denial/error, never silently success ---
    assert [r.step_id for r in result.step_results] == ["dangerous"]
    assert result.step_results[0].driver_result.outcome == DriverOutcome.STOPPED_TOOL_FAILURE
    denied_observation = result.step_results[0].driver_result.turns_run[0].tool_calls[0]["observation"]
    assert denied_observation["status"] == "error"
    assert denied_observation["outcome"] == "denied"

    # --- PlanExecutor's real cascade-skip, unmodified ---
    assert result.plan.get_step("dangerous").status == StepStatus.FAILED
    assert result.plan.get_step("after").status == StepStatus.SKIPPED
    assert plan_executor.all_succeeded(result.plan) is False


def test_plan_step_task_is_resumable_like_any_other_runtime_task(tmp_path: Path) -> None:
    """Recovery compatibility (A-011 brief section 'RECOVERY'): a task
    created by a PlanRunner-driven step is not a special kind of task --
    it's created by the same RuntimeDriver.execute_task() every other
    task is, so it must resume the same way. Proven directly against
    RuntimeDriver.execute_until_stop() (unmodified, A-005/A-009), the
    same mechanism tests/integration/runtime/test_driver_recovery.py
    already proves in general -- not redesigned or duplicated here,
    just confirmed compatible for a plan-step-shaped task_id."""
    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)

    resolver, real_executor = _make_harness(sf, tmp_path)

    plan_id = f"a011-recovery-plan-{uuid.uuid4().hex[:8]}"
    task_id = f"{plan_id}-only-step"

    gateway = FakeModelGateway(
        scripted_responses=[
            {"content": "working", "tool_calls": [{"tool_name": "write_file", "args": {"path": "a.txt", "content": "x"}}]},
            {"content": "done", "tool_calls": []},
        ]
    )

    # First "process": only 1 turn allowed -- stops before completion,
    # exactly like a crash/restart mid-task.
    first_driver = _driver_factory(gateway, sf, resolver, real_executor, max_turns=1)(task_id)
    first_result = first_driver.execute_task(task_id, requirements=["Write a.txt containing x"])
    assert first_result.outcome == DriverOutcome.STOPPED_MAX_TURNS
    assert len(first_result.turns_run) == 1

    # A fresh RuntimeDriver/AgentRuntime (simulating a new process),
    # built the exact same way PlanRunner's driver_factory would build
    # it for this same task_id, resumes and finishes.
    second_driver = _driver_factory(gateway, sf, resolver, real_executor, max_turns=4)(task_id)
    resumed_result = second_driver.execute_until_stop(task_id)

    assert resumed_result.outcome == DriverOutcome.COMPLETED
    assert resumed_result.task.status.value == "completed"
    # Real file, written by the resumed process, still exists.
    assert (tmp_path / "a.txt").exists()


# ---------------------------------------------------------------------------
# Live proof (real Groq for BOTH planning and execution). Skips honestly
# without GROQ_API_KEY, same convention as every other live-gated test
# in this suite (B-009, A-010) -- never fabricated.
# ---------------------------------------------------------------------------

requires_live_groq_key = pytest.mark.skipif(
    not __import__("os").environ.get("GROQ_API_KEY"),
    reason="GROQ_API_KEY not set -- live goal-to-execution test skipped, per A-011's "
    "instruction to report the credential-gated skip honestly rather than fabricate it",
)


@requires_live_groq_key
def test_real_goal_flows_through_plan_runner_to_real_execution_live_groq(tmp_path: Path) -> None:
    from neptune.application.gateway_service import ModelGatewayService
    from neptune.infrastructure.gateway.model_gateway_adapter import ModelGatewayAdapter
    from neptune.infrastructure.models.canonical_registry_adapter import CanonicalRegistryCandidateSource
    from neptune.infrastructure.providers.groq_adapter import GroqAdapter
    from neptune.infrastructure.routing.capability_router import CapabilityRouter
    from core.registry.capability_registry import CapabilityRegistry
    from core.registry.model_registry import ModelRegistry as CanonicalModelRegistry
    from core.registry.provider_registry import ProviderRegistry
    from core.registry.resource_registry import ResourceRegistry
    from core.resolution.capability_resolver import CapabilityResolver
    from core.resolution.provider_resolver import ProviderResolver
    from core.resolution.resource_resolver import ResourceResolver
    from infrastructure.persistence.repositories import (
        SqlAlchemyCapabilityRepository,
        SqlAlchemyModelRepository,
        SqlAlchemyProviderRepository,
        SqlAlchemyResourceRepository,
    )

    engine = make_engine(get_database_url())
    create_all_tables(engine)
    sf = make_session_factory(engine)

    resolver, real_executor = _make_harness(sf, tmp_path)

    cap_resolver = CapabilityResolver(
        CapabilityRegistry(SqlAlchemyCapabilityRepository(sf)),
        ProviderRegistry(SqlAlchemyProviderRepository(sf)),
        CanonicalToolRegistry(SqlAlchemyToolDefinitionRepository(sf)),
    )
    res_resolver = ResourceResolver(
        CapabilityRegistry(SqlAlchemyCapabilityRepository(sf)),
        ProviderRegistry(SqlAlchemyProviderRepository(sf)),
        ResourceRegistry(SqlAlchemyResourceRepository(sf)),
        CanonicalToolRegistry(SqlAlchemyToolDefinitionRepository(sf)),
    )
    prov_resolver = ProviderResolver(
        cap_resolver, res_resolver, ProviderRegistry(SqlAlchemyProviderRepository(sf))
    )
    candidate_source = CanonicalRegistryCandidateSource(
        prov_resolver, CanonicalModelRegistry(SqlAlchemyModelRepository(sf))
    )
    gateway_service = ModelGatewayService(
        registry=candidate_source, router=CapabilityRouter(), adapters={"groq": GroqAdapter()}
    )

    goal_id = f"a011-live-{uuid.uuid4().hex[:8]}"
    planning_gateway = ModelGatewayAdapter(gateway_service, task_id=goal_id, session_id=f"{goal_id}-planning")

    plan_repo = SqlAlchemyPlanRepository(sf)
    plan_executor = PlanExecutor(plan_repo)
    planner = GoalPlanner(model_gateway=planning_gateway, plan_repository=plan_repo, plan_executor=plan_executor)

    def live_driver_factory(task_id: str) -> RuntimeDriver:
        session_id_hint = f"{task_id}-session"
        model_gateway = ModelGatewayAdapter(gateway_service, task_id=task_id, session_id=session_id_hint)
        tool_port = ToolPortAdapter(real_executor, task_id=task_id, session_id=session_id_hint)
        runtime = AgentRuntime(
            task_repo=SqlAlchemyTaskRepository(sf),
            agent_repo=SqlAlchemyAgentRepository(sf),
            session_repo=SqlAlchemySessionRepository(sf),
            turn_repo=SqlAlchemyTurnRepository(sf),
            event_repo=SqlAlchemyEventRepository(sf),
            checkpoint_repo=SqlAlchemyCheckpointRepository(sf),
            model_gateway=model_gateway,
            tool_port=tool_port,
        )

        def context_provider() -> dict:
            return {"available_tools": resolver.available_tools(capability_ids=["tool_use"])}

        return RuntimeDriver(runtime, config=DriverConfig(max_turns=4), context_provider=context_provider)

    runner = PlanRunner(planner=planner, executor=plan_executor, driver_factory=live_driver_factory)

    result = runner.run_goal(
        Goal(
            goal_id=goal_id,
            description='Create a file named hello.txt containing "hello", then read it and verify its contents.',
        )
    )

    assert len(result.plan.steps) >= 1
    assert len(result.step_results) >= 1
    # Live-model behavior variance is possible (same caveat B-009's own
    # live test documents) -- assert the wiring produced a real,
    # non-error outcome for at least the first step, not that every
    # step necessarily succeeded end to end.
    first = result.step_results[0].driver_result
    assert "error" not in (first.turns_run[0].model_response or {})

"""The Neptune CLI through the real production composition (T1/T3).

`neptune.cli.main` is called exactly as `python -m neptune` calls it. The
ONLY substitution is the model (FakeModelGateway via the documented
`model_gateway_factory` seam); everything else is the real composition
root: real PostgreSQL, real registry seeding from 06_REGISTRIES/data,
real ToolOfferingResolver, real RuntimeDriver/AgentRuntime/PlanRunner,
real ToolExecutorService with its default permission policy, real
filesystem + shell tools, and the real CliApprovalProvider (input is
scripted, as a terminal would supply it).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from config.settings import get_database_url
from core.runtime.fakes import FakeModelGateway
from infrastructure.persistence.database import make_engine
from neptune.cli import main


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


def _plan(steps: list[dict]) -> dict:
    return {"content": json.dumps({"steps": steps}), "tool_calls": []}


def _run(tmp_path: Path, goal: str, script: list[dict], answers: list[str] | None = None, extra_args=()):
    gateway = FakeModelGateway(scripted_responses=script)
    out: list[str] = []
    prompts: list[str] = []
    remaining = list(answers or [])

    def input_fn(prompt: str) -> str:
        prompts.append(prompt)
        return remaining.pop(0)

    code = main(
        [goal, "--workspace", str(tmp_path), *extra_args],
        model_gateway_factory=lambda task_id, session_id, concrete_tools: gateway,
        input_fn=input_fn,
        output_fn=out.append,
    )
    return code, gateway, out, prompts


def test_cli_submits_a_goal_and_runs_it_through_the_real_path(tmp_path: Path) -> None:
    goal = 'Create hello.txt containing "hello", then read it back'
    code, gateway, out, prompts = _run(
        tmp_path,
        goal,
        [
            _plan(
                [
                    {"step_id": "write", "title": "Write hello.txt"},
                    {"step_id": "read", "title": "Read hello.txt", "dependencies": ["write"]},
                ]
            ),
            {"content": "writing", "tool_calls": [{"tool_name": "write_file", "args": {"path": "hello.txt", "content": "hello"}}]},
            {"content": "wrote it", "tool_calls": []},
            {"content": "reading", "tool_calls": [{"tool_name": "read_file", "args": {"path": "hello.txt"}}]},
            {"content": "it says hello", "tool_calls": []},
        ],
    )

    assert code == 0, "\n".join(out)
    # Real tools acted on the real workspace.
    assert (tmp_path / "hello.txt").read_text() == "hello"
    assert prompts == [], "an ALLOW-only run must never ask the human"
    text_out = "\n".join(out)
    assert "RESULT: all steps completed with no tool errors" in text_out
    assert "[completed] write" in text_out and "[completed] read" in text_out
    assert "tool write_file: success" in text_out

    step_requests = gateway.requests_received[1:]  # [0] is the planning call
    # T2 through the CLI: every step's model request carries the goal.
    assert all(goal in " ".join(r["requirements"]) for r in step_requests)
    # Dynamic offering via the production composition: filesystem AND shell
    # families come from the canonical catalog, at request time.
    offered = {o["tool_id"] for o in step_requests[0]["available_tools"]}
    assert {"filesystem", "terminal"} <= offered


def test_ask_prompts_the_human_and_approval_executes_the_command(tmp_path: Path) -> None:
    marker = tmp_path / "approved-marker.txt"
    code, _gateway, out, prompts = _run(
        tmp_path,
        "Check curl",
        [
            _plan([{"step_id": "net", "title": "Check curl version"}]),
            {"content": "checking", "tool_calls": [{"tool_name": "run_command", "args": {"command": f"curl --version && echo ran > {marker}"}}]},
            {"content": "done", "tool_calls": []},
        ],
        answers=["y"],
    )

    assert len(prompts) == 1, "ASK must invoke the human approval channel exactly once"
    assert "APPROVAL REQUIRED" in "\n".join(out)
    assert "curl --version" in "\n".join(out), "the user must be shown the command"
    assert marker.exists(), "approved ASK must reach the real shell tool"
    assert code == 0, "\n".join(out)


def test_ask_rejection_prevents_execution_and_fails_the_step(tmp_path: Path) -> None:
    marker = tmp_path / "rejected-marker.txt"
    code, _gateway, out, prompts = _run(
        tmp_path,
        "Check curl",
        [
            _plan([{"step_id": "net", "title": "Check curl version"}]),
            {"content": "checking", "tool_calls": [{"tool_name": "run_command", "args": {"command": f"curl --version; echo ran > {marker}"}}]},
        ],
        answers=["n"],
    )

    assert len(prompts) == 1
    assert not marker.exists(), "a rejected ASK must never reach the shell"
    assert code == 1
    text_out = "\n".join(out)
    assert "[failed] net" in text_out
    assert "RESULT: not all steps completed" in text_out
    assert "all steps completed with no tool errors" not in text_out, "a rejected approval must never be reported as success"


def test_default_deny_is_intact_and_never_prompts(tmp_path: Path) -> None:
    marker = tmp_path / "deny-marker.txt"
    code, _gateway, out, prompts = _run(
        tmp_path,
        "Delete a branch",
        [
            _plan(
                [
                    {"step_id": "del", "title": "Delete remote branch"},
                    {"step_id": "after", "title": "Then more", "dependencies": ["del"]},
                ]
            ),
            {"content": "deleting", "tool_calls": [{"tool_name": "run_command", "args": {"command": f"git push origin --delete x; echo ran > {marker}"}}]},
        ],
    )

    assert prompts == [], "DENY is not askable"
    assert not marker.exists()
    assert code == 1
    text_out = "\n".join(out)
    assert "[failed] del" in text_out
    assert "[skipped] after" in text_out
    assert "all steps completed with no tool errors" not in text_out, "a denied tool must never be reported as success"


def test_allowed_shell_command_runs_for_real(tmp_path: Path) -> None:
    marker = tmp_path / "allow-marker.txt"
    code, _gateway, out, prompts = _run(
        tmp_path,
        "Make a marker",
        [
            _plan([{"step_id": "mk", "title": "Create marker file"}]),
            {"content": "running", "tool_calls": [{"tool_name": "run_command", "args": {"command": f"echo ran > {marker}"}}]},
            {"content": "done", "tool_calls": []},
        ],
    )

    assert code == 0, "\n".join(out)
    assert prompts == []
    assert marker.exists()


def test_model_error_is_reported_as_failure_not_success(tmp_path: Path) -> None:
    code, _gateway, out, _prompts = _run(
        tmp_path,
        "Do a thing",
        [
            _plan([{"step_id": "s", "title": "A step"}]),
            {"content": None, "tool_calls": [], "error": {"error_type": "rate_limited", "message": "429 slow down"}},
        ],
    )

    assert code == 1
    text_out = "\n".join(out)
    assert "[failed] s" in text_out
    assert "model error: 429 slow down" in text_out


def test_unusable_plan_exits_3_and_runs_nothing(tmp_path: Path) -> None:
    code, gateway, out, _prompts = _run(
        tmp_path, "Do a thing", [{"content": "no json here", "tool_calls": []}]
    )
    assert code == 3
    assert "could not produce a valid plan" in "\n".join(out)
    assert len(gateway.requests_received) == 1


def test_usage_errors_exit_2(tmp_path: Path, monkeypatch) -> None:
    out: list[str] = []
    assert main(["   ", "--workspace", str(tmp_path)], model_gateway_factory=lambda *a: None, output_fn=out.append) == 2
    assert main(["goal", "--workspace", str(tmp_path / "missing")], model_gateway_factory=lambda *a: None, output_fn=out.append) == 2
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert main(["goal", "--workspace", str(tmp_path)], output_fn=out.append) == 2
    assert any("GROQ_API_KEY" in line for line in out)


# ---------------------------------------------------------------------------
# MVP closure (Review 009): a failed command must not be reported as success
# ---------------------------------------------------------------------------

def test_failed_command_fails_the_step_and_the_run(tmp_path: Path) -> None:
    """The exact false-success case Reviews 008/008B reproduced: a command
    that exits non-zero, followed by the model saying it is done. The
    step, the dependent step and the CLI result must all reflect the
    failure."""
    code, _gateway, out, prompts = _run(
        tmp_path,
        "Run the tests, then publish",
        [
            _plan(
                [
                    {"step_id": "tests", "title": "Run the tests"},
                    {"step_id": "publish", "title": "Publish", "dependencies": ["tests"]},
                ]
            ),
            {"content": "running", "tool_calls": [{"tool_name": "run_command", "args": {"command": "exit 3"}}]},
            {"content": "Tests complete.", "tool_calls": []},
        ],
    )

    text_out = "\n".join(out)
    assert code == 1
    assert prompts == []
    assert "[failed] tests" in text_out
    assert "[skipped] publish" in text_out
    # The user is shown that the command failed and why -- not "success".
    assert "tool run_command: error (command exited with code 3)" in text_out
    assert "tool run_command: success" not in text_out
    assert "RESULT: not all steps completed" in text_out
    assert "all steps completed with no tool errors" not in text_out


def test_failed_command_is_a_failed_task_in_the_runtime_record(tmp_path: Path) -> None:
    """Not only the printed text: the persisted observation for that turn is
    status 'error' and the driver stopped on it (STOPPED_TOOL_FAILURE),
    so the underlying task/step state is failed, not just the wording."""
    from core.planning.models import StepStatus
    from core.runtime.driver import DriverOutcome
    from neptune.application.composition import build_plan_runner
    from neptune.infrastructure.security.cli_approval import CliApprovalProvider
    from core.planning.models import Goal

    gateway = FakeModelGateway(
        scripted_responses=[
            _plan([{"step_id": "t", "title": "Run the tests"}]),
            {"content": "running", "tool_calls": [{"tool_name": "run_command", "args": {"command": "exit 3"}}]},
            {"content": "Tests complete.", "tool_calls": []},
        ]
    )
    runner = build_plan_runner(
        workspace=tmp_path,
        approval_provider=CliApprovalProvider(ask=lambda _p: "n", out=lambda _t: None),
        model_gateway_factory=lambda task_id, session_id, tools: gateway,
    )
    result = runner.run_goal(Goal(goal_id="g-fail-record", description="Run the tests"))

    step_result = result.step_results[0]
    assert step_result.driver_result.outcome == DriverOutcome.STOPPED_TOOL_FAILURE
    assert result.plan.get_step("t").status == StepStatus.FAILED
    observation = step_result.driver_result.turns_run[0].tool_calls[0]["observation"]
    assert observation["status"] == "error"
    assert observation["result"]["exit_code"] == 3  # evidence preserved in the record
    # The model's "Tests complete." was never even requested: the loop
    # stopped on the failed command, so it cannot paper over it.
    assert len(step_result.driver_result.turns_run) == 1


def test_successful_command_still_completes_the_step(tmp_path: Path) -> None:
    code, _gateway, out, _prompts = _run(
        tmp_path,
        "Say hello",
        [
            _plan([{"step_id": "s", "title": "Echo hello"}]),
            {"content": "running", "tool_calls": [{"tool_name": "run_command", "args": {"command": "echo hello"}}]},
            {"content": "done", "tool_calls": []},
        ],
    )
    text_out = "\n".join(out)
    assert code == 0, text_out
    assert "[completed] s" in text_out
    assert "tool run_command: success" in text_out
    assert "RESULT: all steps completed with no tool errors" in text_out

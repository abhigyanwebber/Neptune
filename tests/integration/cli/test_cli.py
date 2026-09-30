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
    assert "RESULT: all steps succeeded" in text_out
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
            {"content": "checking", "tool_calls": [{"tool_name": "run_command", "args": {"command": f"curl --version; echo ran > {marker}"}}]},
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
    assert "RESULT: not all steps succeeded" in text_out


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

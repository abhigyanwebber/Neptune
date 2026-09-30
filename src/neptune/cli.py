"""Neptune command-line entry point (T1).

Like every other part of this repository, run with `src` on PYTHONPATH
(pytest.ini sets this for the test suite; nothing here changes that
convention):

    $env:PYTHONPATH = "src"                        # PowerShell
    python -m neptune "Create hello.txt containing hello, then read it back" `
        --workspace ./sandbox-dir

Thin by design: parse arguments, compose (neptune.application.composition),
run one goal through GoalPlanner -> PlanRunner -> RuntimeDriver, print the
outcome. Human approval for ASK-classified actions is a CliApprovalProvider
prompt on the same terminal. Requires PostgreSQL (docker compose up -d) and,
for the default real model, GROQ_API_KEY.

Exit codes: 0 every step succeeded; 1 plan ran but not all steps
succeeded; 2 usage/environment problem; 3 the goal could not be turned
into a valid plan.
"""
from __future__ import annotations

import argparse
import os
import uuid
from pathlib import Path
from typing import Callable, Optional, Sequence

from core.planning.errors import PlanValidationError
from core.planning.models import Goal, StepStatus
from neptune.application.composition import (
    DEFAULT_MAX_TURNS_PER_STEP,
    DEFAULT_REGISTRY_DIR,
    ModelGatewayFactory,
    build_plan_runner,
)
from neptune.infrastructure.security.cli_approval import CliApprovalProvider


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="neptune", description="Give Neptune a goal; it plans and executes it.")
    p.add_argument("goal", help="what you want done, in plain language")
    p.add_argument("--workspace", default=".", help="directory the agent may read/write/run commands in (default: current directory)")
    p.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS_PER_STEP, help="model turns allowed per plan step")
    p.add_argument("--registry-dir", default=str(DEFAULT_REGISTRY_DIR), help="canonical registry seed data directory")
    return p


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    model_gateway_factory: Optional[ModelGatewayFactory] = None,
    session_factory=None,
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    """`model_gateway_factory`, `session_factory`, `input_fn` and `output_fn`
    exist so tests can drive the real composition without a terminal or a
    live model; the defaults are the production behavior."""
    args = _parser().parse_args(argv)

    goal_text = args.goal.strip()
    if not goal_text:
        output_fn("error: goal must not be empty")
        return 2

    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        output_fn(f"error: workspace is not a directory: {workspace}")
        return 2

    if model_gateway_factory is None and not os.environ.get("GROQ_API_KEY"):
        output_fn("error: GROQ_API_KEY is not set (needed for the default model provider)")
        return 2

    runner = build_plan_runner(
        workspace=workspace,
        approval_provider=CliApprovalProvider(ask=input_fn, out=output_fn),
        registry_dir=Path(args.registry_dir),
        session_factory=session_factory,
        model_gateway_factory=model_gateway_factory,
        max_turns_per_step=args.max_turns,
    )

    goal = Goal(goal_id=f"goal-{uuid.uuid4().hex[:8]}", description=goal_text)
    output_fn(f"goal:      {goal_text}")
    output_fn(f"workspace: {workspace}")
    output_fn("planning...")

    try:
        result = runner.run_goal(goal)
    except PlanValidationError as exc:
        output_fn(f"error: could not produce a valid plan: {exc}")
        return 3

    output_fn(f"plan {result.plan.plan_id}: {len(result.plan.steps)} step(s)")
    ran = {r.step_id: r for r in result.step_results}
    for step in result.plan.steps:
        output_fn(f"  [{step.status.value}] {step.step_id}: {step.title}")
        step_result = ran.get(step.step_id)
        if step_result is None:
            continue
        driver_result = step_result.driver_result
        for turn in driver_result.turns_run:
            for call in turn.tool_calls:
                request = call.get("request") or {}
                observation = call.get("observation") or {}
                output_fn(
                    f"      tool {request.get('tool_name')}: "
                    f"{observation.get('outcome') or observation.get('status')}"
                    + (f" ({observation.get('error_message')})" if observation.get("error_message") else "")
                )
        last = driver_result.turns_run[-1].model_response if driver_result.turns_run else None
        if last and last.get("error"):
            output_fn(f"      model error: {last['error'].get('message')}")
        elif last and last.get("content"):
            output_fn(f"      model: {str(last['content']).strip()[:300]}")

    succeeded = all(s.status == StepStatus.COMPLETED for s in result.plan.steps)
    output_fn("RESULT: " + ("all steps succeeded" if succeeded else "not all steps succeeded"))
    return 0 if succeeded else 1

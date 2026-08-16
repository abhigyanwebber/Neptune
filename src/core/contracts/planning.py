"""Plan repository contract (Protocol).

Pure interface, zero infrastructure imports -- same pattern as
core/contracts/repositories.py and core/contracts/registry.py.
infrastructure/persistence provides the Postgres-backed implementation.
"""
from __future__ import annotations

from typing import Optional, Protocol

from core.planning.models import Plan


class PlanRepository(Protocol):
    def create(self, plan: Plan) -> None: ...
    def get(self, plan_id: str) -> Optional[Plan]: ...
    def update(self, plan: Plan) -> None: ...
    def list_for_goal(self, goal_id: str) -> list[Plan]: ...

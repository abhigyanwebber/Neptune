"""SQLAlchemy implementation of the Plan repository contract.

Same one-transaction-per-call pattern as sqlalchemy_repositories.py and
registry_repositories.py (ADR-A-002). Only this module imports SQLAlchemy
for the planning side; core/planning and core/contracts/planning.py stay
persistence-agnostic.

Steps are stored as a single JSON column (PlanModel.steps) rather than a
separate steps table -- consistent with how Turn.tool_calls already
persists as JSON (Stage 0/1). A Plan's steps are always read/written as a
whole with the Plan, so there's no query pattern that needs per-step rows.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as SqlAlchemySession
from sqlalchemy.orm import sessionmaker

from core.planning.models import Plan

from ..models.orm import PlanModel


class SqlAlchemyPlanRepository:
    def __init__(self, session_factory: sessionmaker[SqlAlchemySession]) -> None:
        self._session_factory = session_factory

    def create(self, plan: Plan) -> None:
        with self._session_factory() as db:
            db.add(_plan_to_model(plan))
            db.commit()

    def get(self, plan_id: str) -> Optional[Plan]:
        with self._session_factory() as db:
            model = db.get(PlanModel, plan_id)
            return _model_to_plan(model) if model else None

    def update(self, plan: Plan) -> None:
        with self._session_factory() as db:
            model = db.get(PlanModel, plan.plan_id)
            if model is None:
                raise ValueError(f"Plan not found: {plan.plan_id}")
            model.steps = [s.to_dict() for s in plan.steps]
            model.updated_at = plan.updated_at
            db.commit()

    def list_for_goal(self, goal_id: str) -> list[Plan]:
        with self._session_factory() as db:
            stmt = select(PlanModel).where(PlanModel.goal_id == goal_id)
            return [_model_to_plan(m) for m in db.scalars(stmt)]


def _utc(value: Optional[datetime]) -> Optional[datetime]:
    """Normalize a datetime read back from the DB to timezone-aware UTC --
    SQLite returns naive datetimes even for DateTime(timezone=True)
    columns, unlike Postgres. See the identical helper and rationale in
    sqlalchemy_repositories.py."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _plan_to_model(p: Plan) -> PlanModel:
    return PlanModel(
        plan_id=p.plan_id,
        goal_id=p.goal_id,
        steps=[s.to_dict() for s in p.steps],
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _model_to_plan(m: PlanModel) -> Plan:
    return Plan.from_dict(
        {
            "plan_id": m.plan_id,
            "goal_id": m.goal_id,
            "steps": m.steps,
            "created_at": _utc(m.created_at),
            "updated_at": _utc(m.updated_at),
        }
    )

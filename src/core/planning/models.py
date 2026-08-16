"""Planning domain objects: Goal, Plan, PlanStep, StepStatus.

Plain dataclasses, zero infrastructure/provider imports -- same pattern as
core/domain/*.py (Task, Session, Turn, etc.). This is contracts-and-data
only: nothing here reasons about *how* to decompose a goal into steps
(A-007 brief: "Do not build sophisticated reasoning... Do not build
provider-specific planning prompts"). A Plan's steps are supplied by
whatever constructs it -- this module only defines what a Plan/PlanStep
*is* and how it serializes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Goal:
    goal_id: str
    description: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Goal":
        return cls(
            goal_id=data["goal_id"],
            description=data["description"],
            created_at=_parse_dt(data["created_at"]),
        )


@dataclass
class PlanStep:
    step_id: str
    title: str
    description: str = ""
    capability_id: str = ""
    status: StepStatus = StepStatus.PENDING
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "title": self.title,
            "description": self.description,
            "capability_id": self.capability_id,
            "status": self.status.value,
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlanStep":
        return cls(
            step_id=data["step_id"],
            title=data["title"],
            description=data.get("description", ""),
            capability_id=data.get("capability_id", ""),
            status=StepStatus(data.get("status", "pending")),
            dependencies=list(data.get("dependencies") or []),
        )


@dataclass
class Plan:
    plan_id: str
    goal_id: str
    steps: list[PlanStep] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    def get_step(self, step_id: str) -> PlanStep:
        for step in self.steps:
            if step.step_id == step_id:
                return step
        raise KeyError(f"No such step in plan {self.plan_id}: {step_id}")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "plan_id": self.plan_id,
            "goal_id": self.goal_id,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at.isoformat(),
        }
        if self.updated_at is not None:
            payload["updated_at"] = self.updated_at.isoformat()
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Plan":
        return cls(
            plan_id=data["plan_id"],
            goal_id=data["goal_id"],
            steps=[PlanStep.from_dict(s) for s in data.get("steps") or []],
            created_at=_parse_dt(data["created_at"]),
            updated_at=_parse_dt(data["updated_at"]) if data.get("updated_at") else None,
        )


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)

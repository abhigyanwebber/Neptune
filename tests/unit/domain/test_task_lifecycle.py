import pytest

from core.domain.task import Task, TaskStatus


def test_legal_transition_updates_status_and_timestamp():
    task = Task(task_id="t1", status=TaskStatus.CREATED)
    assert task.updated_at is None
    task.transition_to(TaskStatus.QUEUED)
    assert task.status == TaskStatus.QUEUED
    assert task.updated_at is not None


def test_illegal_transition_raises():
    task = Task(task_id="t1", status=TaskStatus.COMPLETED)
    with pytest.raises(ValueError):
        task.transition_to(TaskStatus.EXECUTING)


@pytest.mark.parametrize(
    "start,end",
    [
        (TaskStatus.CREATED, TaskStatus.QUEUED),
        (TaskStatus.QUEUED, TaskStatus.PLANNING),
        (TaskStatus.PLANNING, TaskStatus.EXECUTING),
        (TaskStatus.EXECUTING, TaskStatus.VERIFYING),
        (TaskStatus.VERIFYING, TaskStatus.COMPLETED),
    ],
)
def test_happy_path_transitions(start, end):
    task = Task(task_id="t1", status=start)
    task.transition_to(end)
    assert task.status == end

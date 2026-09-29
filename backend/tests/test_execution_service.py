from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.models.execution import Execution
from app.schemas.execution import UpdateExecutionStatusRequest
from app.services.execution_service import (
    ExecutionNotFound,
    InvalidTransition,
    change_status,
)


def make_execution(db, status: str) -> Execution:
    """Persist an execution already sitting in the given status."""
    execution = Execution(
        id=str(uuid4()),
        agent_name="recon-agent",
        model="claude-opus-5",
        priority="high",
        task_type="security_analysis",
        input_text="Scan the target.",
        status=status,
        created_at=datetime.now(timezone.utc),
    )
    db.add(execution)
    db.commit()
    return execution


def test_completed_execution_cannot_go_back_to_running(db_session):
    # Arrange
    execution = make_execution(db_session, status="completed")
    payload = UpdateExecutionStatusRequest(status="running")

    # Act + Assert
    with pytest.raises(InvalidTransition):
        change_status(db_session, execution.id, payload)


def test_unknown_execution_raises_not_found(db_session):
    # Arrange
    payload = UpdateExecutionStatusRequest(status="running")

    # Act + Assert
    with pytest.raises(ExecutionNotFound):
        change_status(db_session, uuid4(), payload)


def test_starting_a_pending_execution_sets_started_at(db_session):
    # Arrange
    execution = make_execution(db_session, status="pending")
    payload = UpdateExecutionStatusRequest(status="running")

    # Act
    result = change_status(db_session, execution.id, payload)

    # Assert
    assert result.status == "running"
    assert result.started_at is not None

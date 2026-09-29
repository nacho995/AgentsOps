from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.execution import Execution
from app.schemas.execution import UpdateExecutionStatusRequest

ALLOWED_TRANSITIONS = {
    "pending": {"running", "cancelled"},
    "running": {"completed", "failed", "cancelled"},
    "completed": set(),
    "failed": set(),
    "cancelled": set(),
}


class ExecutionNotFound(Exception):
    pass


class InvalidTransition(Exception):
    pass


def change_status(db: Session, execution_id: UUID, payload: UpdateExecutionStatusRequest) -> Execution:
    execution = db.get(Execution, str(execution_id))

    if execution is None:
        raise ExecutionNotFound(f"Execution {execution_id} not found")

    current_status = execution.status
    next_status = payload.status.value

    if next_status not in ALLOWED_TRANSITIONS[current_status]:
        raise InvalidTransition(f"Cannot change status from {current_status} to {next_status}")

    now = datetime.now(timezone.utc)
    execution.status = next_status
    if next_status == "running":
        execution.started_at = now
    if next_status in {"completed", "failed", "cancelled"}:
        execution.finished_at = now
    if next_status == "completed":
        execution.input_tokens = payload.input_tokens
        execution.output_tokens = payload.output_tokens
        execution.cost = payload.cost
    if next_status == "failed":
        execution.error_type = payload.error_type
        execution.error_retryable = payload.error_retryable

    db.commit()
    db.refresh(execution)
    return execution
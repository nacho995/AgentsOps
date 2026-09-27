from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.execution import Execution
from app.schemas.execution import (
    CreateExecutionRequest,
    ExecutionResponse,
    ExecutionStatus,
)
from app.schemas.execution import UpdateExecutionStatusRequest

router = APIRouter()


@router.post(
    "",
    response_model=ExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_execution(
    payload: CreateExecutionRequest,
    db: Session = Depends(get_db),
) -> Execution:
    """Create and persist a new pending agent execution."""

    execution = Execution(
        id=str(uuid4()),
        agent_name=payload.agent_name,
        model=payload.model,
        priority=payload.priority.value,
        task_type=payload.task_type.value,
        input_text=payload.input_text,
        status=ExecutionStatus.PENDING.value,
        created_at=datetime.now(timezone.utc),
    )

    db.add(execution)
    db.commit()
    db.refresh(execution)

    return execution


@router.get(
    "",
    response_model=list[ExecutionResponse],
)
def list_executions(
    db: Session = Depends(get_db),
) -> list[Execution]:
    """Return all persisted agent executions."""

    statement = select(Execution).order_by(Execution.created_at.desc())

    return list(db.scalars(statement).all())


@router.get(
    "/{execution_id}",
    response_model=ExecutionResponse,
)
def get_execution(
    execution_id: UUID,
    db: Session = Depends(get_db),
) -> Execution:
    """Return one persisted execution by its identifier."""

    execution = db.get(Execution, str(execution_id))

    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    return execution
@router.patch(
    "/{execution_id}/status",
    response_model=ExecutionResponse,
)
def update_execution_status(
    execution_id: UUID,
    payload: UpdateExecutionStatusRequest,
    db: Session = Depends(get_db),
) -> Execution:
    """Update an execution status while enforcing its lifecycle."""

    execution = db.get(Execution, str(execution_id))

    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found",
        )

    allowed_transitions = {
        "pending": {"running", "cancelled"},
        "running": {"completed", "failed", "cancelled"},
        "completed": set(),
        "failed": set(),
        "cancelled": set(),
    }

    current_status = execution.status
    next_status = payload.status.value

    if next_status not in allowed_transitions[current_status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot change status from "
                f"{current_status} to {next_status}"
            ),
        )

    now = datetime.now(timezone.utc)

    execution.status = next_status

    if next_status == "running":
        execution.started_at = now

    if next_status in {"completed", "failed", "cancelled"}:
        execution.finished_at = now

    # Metering is only recorded on a successful finish: a completed run is the
    # only moment a real agent knows its token usage and cost.
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
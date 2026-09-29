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
from app.services.execution_service import ExecutionNotFound, InvalidTransition, change_status

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
@router.patch("/{execution_id}/status", response_model=ExecutionResponse)
def update_execution_status(
    execution_id: UUID,
    payload: UpdateExecutionStatusRequest,
    db: Session = Depends(get_db),
) -> Execution: 
    """Update an execution status while enforcing its lifecycle."""
    try:
        return change_status(db, execution_id, payload)
    except ExecutionNotFound:
        raise HTTPException(status_code=404, detail="Execution not found")
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
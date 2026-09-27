"""Pydantic schemas for the executions API.

Three request/response contracts live here:

* ``CreateExecutionRequest``       -- payload to register a new execution.
* ``UpdateExecutionStatusRequest`` -- payload to advance the lifecycle and,
  when finishing, attach the metering data (tokens + cost).
* ``ExecutionResponse``            -- the serialized view returned to clients.

The enums are shared with the SQLAlchemy layer as plain string values so the
database stays human-readable.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Priority(str, Enum):
    """How urgent an execution is relative to the rest of the queue."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskType(str, Enum):
    """The kind of work the agent was asked to perform."""

    SECURITY_ANALYSIS = "security_analysis"
    SUMMARIZATION = "summarization"
    CLASSIFICATION = "classification"
    CODE_REVIEW = "code_review"
    INCIDENT_TRIAGE = "incident_triage"


class ExecutionStatus(str, Enum):
    """Lifecycle stages an execution moves through.

    Transitions are enforced server-side; see ``api/executions.py``.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CreateExecutionRequest(BaseModel):
    """Client payload to enqueue a new, still-pending execution."""

    agent_name: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    priority: Priority = Priority.MEDIUM
    task_type: TaskType
    input_text: str = Field(min_length=1, max_length=10_000)


class UpdateExecutionStatusRequest(BaseModel):
    """Client payload to advance an execution to its next lifecycle stage.

    The metering fields (``input_tokens``, ``output_tokens``, ``cost``) are
    optional and only meaningful when moving to ``completed`` -- that is when a
    real agent run would know how many tokens it burned and what it cost.
    """

    status: ExecutionStatus
    error_type: str | None = Field(default=None, max_length=100)
    error_retryable: bool | None = None
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    cost: Decimal | None = Field(default=None, ge=0)


class ExecutionResponse(BaseModel):
    """Serialized execution, read straight from the ORM model."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_name: str
    model: str
    priority: Priority
    task_type: TaskType
    input_text: str
    status: ExecutionStatus
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost: float | None = None
    error_type: str | None = None
    error_retryable: bool | None = None

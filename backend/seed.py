"""Populate the database with a realistic set of demo executions.

Run it once against a fresh database so the dashboard has something to show:

    python seed.py

It wipes the ``executions`` table first, so it is safe to re-run. This is
sample data for the demo -- there is no real agent behind the numbers.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from app.db.database import Base, SessionLocal, engine
from app.models.execution import Execution

# A representative instruction per task type, so the board does not read as one
# row copied eleven times.
_INSTRUCTIONS = {
    "security_analysis": (
        "Scan the exposed API surface and rank findings by CVSS severity."
    ),
    "summarization": (
        "Summarise the incident post-mortem into five decision-ready bullets."
    ),
    "classification": (
        "Classify the last 2,000 support tickets by product area and urgency."
    ),
    "code_review": (
        "Review the pull-request diff for security and concurrency defects."
    ),
    "incident_triage": (
        "Triage the pager alert: assess blast radius and recommend next action."
    ),
}

# One dict per execution. `age_min` is how long ago it was created; `dur_s` is
# how long the run took (only used once it has started).
_DEMO_ROWS = [
    {"agent": "recon-agent", "model": "claude-opus-5", "priority": "critical",
     "task": "security_analysis", "status": "completed", "age_min": 242,
     "dur_s": 214, "in": 3120, "out": 890, "cost": "0.061"},
    {"agent": "triage-agent", "model": "claude-sonnet-5", "priority": "high",
     "task": "incident_triage", "status": "completed", "age_min": 205,
     "dur_s": 63, "in": 1450, "out": 410, "cost": "0.018"},
    {"agent": "summarizer", "model": "claude-haiku-4-5", "priority": "low",
     "task": "summarization", "status": "completed", "age_min": 181,
     "dur_s": 47, "in": 8200, "out": 1200, "cost": "0.009"},
    {"agent": "code-reviewer", "model": "claude-opus-5", "priority": "medium",
     "task": "code_review", "status": "completed", "age_min": 150,
     "dur_s": 168, "in": 5600, "out": 1740, "cost": "0.104"},
    {"agent": "classifier", "model": "claude-haiku-4-5", "priority": "medium",
     "task": "classification", "status": "completed", "age_min": 121,
     "dur_s": 12, "in": 640, "out": 90, "cost": "0.001"},
    {"agent": "recon-agent", "model": "claude-sonnet-5", "priority": "high",
     "task": "security_analysis", "status": "failed", "age_min": 95,
     "dur_s": 31, "error": "rate_limit", "retryable": True},
    {"agent": "incident-responder", "model": "claude-opus-5",
     "priority": "critical", "task": "incident_triage", "status": "failed",
     "age_min": 70, "dur_s": 9, "error": "context_length_exceeded",
     "retryable": False},
    {"agent": "code-reviewer", "model": "claude-sonnet-5", "priority": "medium",
     "task": "code_review", "status": "running", "age_min": 25, "dur_s": None},
    {"agent": "triage-agent", "model": "claude-opus-5", "priority": "high",
     "task": "incident_triage", "status": "running", "age_min": 12,
     "dur_s": None},
    {"agent": "summarizer", "model": "claude-haiku-4-5", "priority": "low",
     "task": "summarization", "status": "pending", "age_min": 6, "dur_s": None},
    {"agent": "classifier", "model": "claude-sonnet-5", "priority": "medium",
     "task": "classification", "status": "cancelled", "age_min": 3,
     "dur_s": 4},
]


def _build_execution(row: dict) -> Execution:
    now = datetime.now(timezone.utc)
    created_at = now - timedelta(minutes=row["age_min"])
    status = row["status"]

    started_at = None
    finished_at = None
    if status in {"running", "completed", "failed", "cancelled"}:
        started_at = created_at + timedelta(seconds=15)
    if status in {"completed", "failed", "cancelled"} and row["dur_s"]:
        finished_at = started_at + timedelta(seconds=row["dur_s"])

    cost = row.get("cost")

    return Execution(
        id=str(uuid4()),
        agent_name=row["agent"],
        model=row["model"],
        priority=row["priority"],
        task_type=row["task"],
        input_text=_INSTRUCTIONS[row["task"]],
        status=status,
        created_at=created_at,
        started_at=started_at,
        finished_at=finished_at,
        input_tokens=row.get("in"),
        output_tokens=row.get("out"),
        cost=Decimal(cost) if cost is not None else None,
        error_type=row.get("error"),
        error_retryable=row.get("retryable"),
    )


def main() -> None:
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        deleted = session.query(Execution).delete()
        session.add_all(_build_execution(row) for row in _DEMO_ROWS)
        session.commit()
        print(
            f"Seeded {len(_DEMO_ROWS)} demo executions "
            f"(removed {deleted} existing rows)."
        )
    finally:
        session.close()


if __name__ == "__main__":
    main()

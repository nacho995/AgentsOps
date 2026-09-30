"""End-to-end tests for the executions API.

They exercise the whole HTTP surface (routing, validation, persistence and the
status state machine) through a real TestClient, so a green run means the API
behaves as advertised, not just that individual functions return the right
value.
"""

from uuid import UUID

from fastapi import status

from tests.conftest import build_execution_payload


def test_health_check_reports_ok(client) -> None:
    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"status": "ok"}


def test_create_execution_starts_pending(client) -> None:
    response = client.post("/executions", json=build_execution_payload())

    assert response.status_code == status.HTTP_201_CREATED
    body = response.json()

    assert UUID(body["id"])  # a well-formed identifier was assigned
    assert body["status"] == "pending"
    assert body["agent_name"] == "recon-agent"
    assert body["created_at"] is not None
    assert body["started_at"] is None
    assert body["finished_at"] is None
    assert body["cost"] is None


def test_create_execution_rejects_unknown_task_type(client) -> None:
    payload = build_execution_payload(task_type="not_a_real_task")

    response = client.post("/executions", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_create_execution_rejects_blank_agent_name(client) -> None:
    payload = build_execution_payload(agent_name="")

    response = client.post("/executions", json=payload)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_list_executions_returns_newest_first(client) -> None:
    first = client.post(
        "/executions", json=build_execution_payload(agent_name="first")
    ).json()
    second = client.post(
        "/executions", json=build_execution_payload(agent_name="second")
    ).json()

    response = client.get("/executions")

    assert response.status_code == status.HTTP_200_OK
    ids = [item["id"] for item in response.json()]
    assert ids == [second["id"], first["id"]]


def test_get_execution_returns_the_created_row(client) -> None:
    created = client.post("/executions", json=build_execution_payload()).json()

    response = client.get(f"/executions/{created['id']}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["id"] == created["id"]


def test_get_unknown_execution_returns_404(client) -> None:
    response = client.get(f"/executions/{UUID(int=0)}")

    assert response.status_code == status.HTTP_404_NOT_FOUND


def test_get_execution_rejects_malformed_id(client) -> None:
    response = client.get("/executions/not-a-uuid")

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_start_execution_sets_started_at(client) -> None:
    created = client.post("/executions", json=build_execution_payload()).json()

    response = client.patch(
        f"/executions/{created['id']}/status",
        json={"status": "running"},
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "running"
    assert body["started_at"] is not None
    assert body["finished_at"] is None


def test_complete_execution_records_metering(client) -> None:
    created = client.post("/executions", json=build_execution_payload()).json()
    client.patch(
        f"/executions/{created['id']}/status", json={"status": "running"}
    )

    response = client.patch(
        f"/executions/{created['id']}/status",
        json={
            "status": "completed",
            "input_tokens": 1200,
            "output_tokens": 350,
            "cost": 0.0185,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "completed"
    assert body["finished_at"] is not None
    assert body["input_tokens"] == 1200
    assert body["output_tokens"] == 350
    assert body["cost"] == "0.018500"


def test_fail_execution_records_error_details(client) -> None:
    created = client.post("/executions", json=build_execution_payload()).json()
    client.patch(
        f"/executions/{created['id']}/status", json={"status": "running"}
    )

    response = client.patch(
        f"/executions/{created['id']}/status",
        json={
            "status": "failed",
            "error_type": "rate_limit",
            "error_retryable": True,
        },
    )

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_type"] == "rate_limit"
    assert body["error_retryable"] is True
    assert body["finished_at"] is not None


def test_illegal_transition_is_rejected(client) -> None:
    """A pending execution cannot jump straight to completed."""

    created = client.post("/executions", json=build_execution_payload()).json()

    response = client.patch(
        f"/executions/{created['id']}/status",
        json={"status": "completed"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_terminal_state_cannot_transition(client) -> None:
    created = client.post("/executions", json=build_execution_payload()).json()
    client.patch(
        f"/executions/{created['id']}/status", json={"status": "cancelled"}
    )

    response = client.patch(
        f"/executions/{created['id']}/status",
        json={"status": "running"},
    )

    assert response.status_code == status.HTTP_409_CONFLICT


def test_update_status_on_unknown_execution_returns_404(client) -> None:
    response = client.patch(
        f"/executions/{UUID(int=0)}/status",
        json={"status": "running"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND

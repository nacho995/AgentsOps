# AgentOps Observatory

A small full-stack dashboard to **track and observe AI agent executions** — their
lifecycle, cost and token usage. Built as a portfolio project to show an
end-to-end slice: a typed REST API with a server-enforced state machine on the
back, and a modern signal-based Angular dashboard on the front.

![AgentOps Observatory dashboard](docs/dashboard.png)

<p>
  <img alt="Angular" src="https://img.shields.io/badge/Angular-22-dd0031?logo=angular&logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.13-3776ab?logo=python&logoColor=white">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-6.0-3178c6?logo=typescript&logoColor=white">
  <img alt="SQLAlchemy" src="https://img.shields.io/badge/SQLAlchemy-2.0-d71f00">
  <img alt="Tests" src="https://img.shields.io/badge/tests-17%20back%20%2B%205%20front-0f9d6c">
</p>

---

## What it does

Each **execution** represents one run of an AI agent: which agent, which model,
the task type, the priority and the instruction. The dashboard lets you:

- **Register** a new execution through a validated form.
- **Advance its lifecycle** — start it, complete it, fail it or cancel it — with
  the allowed transitions enforced on the server.
- **See live metrics** — total, in-progress, completed, failed and accumulated
  cost — recomputed reactively from the execution list.
- **Inspect metering** — input/output tokens and cost are recorded when a run
  completes; the failure reason is recorded when it fails.

### Execution lifecycle

The status transitions are enforced by the API — an illegal jump returns
`409 Conflict`, never a silently corrupted row.

```mermaid
stateDiagram-v2
    [*] --> pending
    pending --> running
    pending --> cancelled
    running --> completed
    running --> failed
    running --> cancelled
    completed --> [*]
    failed --> [*]
    cancelled --> [*]
```

---

## Architecture

A monorepo with two independent workspaces:

```
Bases/
├── docker-compose.yml  PostgreSQL 17 for local development
├── backend/          FastAPI + SQLAlchemy REST API (PostgreSQL)
│   ├── app/
│   │   ├── main.py            app wiring + CORS + health check
│   │   ├── api/executions.py  HTTP routes; maps domain errors to 404/409
│   │   ├── services/          business rules (status state machine)
│   │   ├── models/            SQLAlchemy ORM model
│   │   ├── schemas/           Pydantic request/response contracts
│   │   └── db/                engine + session dependency (reads DATABASE_URL)
│   ├── alembic/               schema migrations
│   ├── tests/                 pytest suite (isolated in-memory DB)
│   └── seed.py                demo data loader
└── frontend/         Angular 22 dashboard (standalone, signals)
    └── src/app/
        ├── app.ts             root component (signals + computed metrics)
        ├── services/          typed HttpClient wrapper
        └── models/            shared TypeScript contracts
```

The frontend talks to the backend over plain REST (`http://127.0.0.1:8000`).
The backend persists to PostgreSQL, run locally with Docker Compose. The schema
is owned by Alembic migrations, not created at startup. The route layer only
translates HTTP; the lifecycle rules live in `services/` and raise domain
exceptions, so they can be tested (and reused) without the API.

---

## Tech stack

| Layer     | Choices                                                                 |
| --------- | ----------------------------------------------------------------------- |
| Frontend  | Angular 22 (standalone components, signals, reactive forms), TypeScript |
| Backend   | FastAPI, Pydantic v2, SQLAlchemy 2.0 (typed `Mapped[...]` models)       |
| Database  | PostgreSQL 17 (Docker Compose), Alembic migrations                      |
| Testing   | pytest + Starlette `TestClient` (backend), Vitest (frontend)            |
| Tooling   | Docker Compose, Prettier, Angular CLI, uvicorn                          |

---

## Getting started

### 1. Database

```bash
docker compose up -d                 # PostgreSQL on localhost:5434
```

The container publishes on host port **5434** rather than 5432, so it does not
collide with a PostgreSQL installed natively on the machine.

### 2. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env                 # DATABASE_URL for the container above
alembic upgrade head                 # create the tables
python seed.py                       # optional: load demo executions
uvicorn app.main:app --reload        # http://127.0.0.1:8000
```

Interactive API docs are served at `http://127.0.0.1:8000/docs`.

### 3. Frontend

```bash
cd frontend
npm install
npm start                            # http://localhost:4200
```

Open `http://localhost:4200` with the backend running.

---

## API reference

Base URL: `http://127.0.0.1:8000`

| Method  | Endpoint                    | Description                                          |
| ------- | --------------------------- | ---------------------------------------------------- |
| `GET`   | `/health`                   | Service health check.                                |
| `POST`  | `/executions`               | Register a new execution (starts `pending`). `201`.  |
| `GET`   | `/executions`               | List every execution, newest first.                  |
| `GET`   | `/executions/{id}`          | Fetch a single execution. `404` if unknown.          |
| `PATCH` | `/executions/{id}/status`   | Advance the lifecycle. `409` on an illegal transition.|

On a transition to `completed`, the PATCH body may carry `input_tokens`,
`output_tokens` and `cost`; on a transition to `failed`, it may carry
`error_type` and `error_retryable`.

---

## Testing

Backend — 14 end-to-end API tests covering routing, validation, persistence and
the status state machine, plus unit tests for the service layer that call it
directly without HTTP. Every test runs against a throwaway in-memory SQLite
database, so the suite needs neither Docker nor a running PostgreSQL:

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Frontend — component and service specs with Angular's `HttpTestingController`:

```bash
cd frontend
npm test
```

---

## Notes

- The token/cost figures shown when completing a run from the UI are **simulated
  metering** — there is no real LLM behind the dashboard. The API itself accepts
  and stores whatever metering the caller reports, so a real agent runner could
  post its actual usage.
- Schema changes go through Alembic: change the model, run
  `alembic revision --autogenerate -m "..."`, review the generated file, then
  `alembic upgrade head`. `create_all` is not used because it never alters
  existing tables.
- Without a `DATABASE_URL` the backend falls back to a local SQLite file, which
  is handy for a quick look but is not the supported setup.

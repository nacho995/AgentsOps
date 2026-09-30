from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="AgentOps Observatory API",
    version="0.1.0",
)

# The Angular dev server can be reached as either host; allow both so a fresh
# clone works without a CORS surprise.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "ok"}

from app.api.executions import router as executions_router

app.include_router(
    executions_router,
    prefix="/executions",
    tags=["executions"],
)
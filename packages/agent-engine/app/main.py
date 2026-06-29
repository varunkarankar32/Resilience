"""
ResilienceAI Agent Engine — FastAPI Backend
LLM-powered SRE incident diagnosis engine with LangGraph orchestration.

Ports the JanShakti-AI main.py pattern:
  - FastAPI app factory with lifespan events
  - CORS middleware for dashboard + gateway
  - Graceful MongoDB/Qdrant startup/shutdown
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.lib.mongo import init_mongo, close_mongo
from app.lib.qdrant import init_qdrant, close_qdrant


def _resolve_cors_origins(raw_value: str) -> list[str]:
    raw = (raw_value or "*").strip()
    if raw == "*":
        return ["*"]

    configured = [item.strip() for item in raw.split(",") if item.strip()]
    local_dev = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4000",
        "http://127.0.0.1:4000",
    ]
    merged = configured + [origin for origin in local_dev if origin not in configured]
    return merged


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — handles startup and shutdown connections."""
    # Startup
    print("=" * 60)
    print("  ResilienceAI — Agent Engine")
    print("=" * 60)

    try:
        await init_mongo()
    except Exception as exc:
        print(f"[WARN] MongoDB initialization failed: {exc}")
        print("[WARN] App will start but diagnosis endpoints may fail.")

    try:
        await init_qdrant()
    except Exception as exc:
        print(f"[WARN] Qdrant initialization failed: {exc}")
        print("[WARN] Runbook search will be unavailable.")

    print(f"[Agent Engine] Listening on http://0.0.0.0:{settings.agent_engine_port}")
    print(f"[Agent Engine] API Docs: http://localhost:{settings.agent_engine_port}/docs")
    print("=" * 60)

    yield

    # Shutdown
    await close_mongo()
    await close_qdrant()
    print("[Agent Engine] Shutdown complete")


app = FastAPI(
    title="ResilienceAI — Agent Engine API",
    description="LLM-powered SRE incident diagnosis and remediation engine",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS
cors_origins = _resolve_cors_origins(settings.cors_origins)
allow_credentials = cors_origins != ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from app.routers import diagnosis  # noqa: E402

app.include_router(diagnosis.router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "name": "ResilienceAI — Agent Engine API",
        "version": "1.0.0",
        "description": "LLM-powered SRE incident diagnosis and remediation engine",
        "docs": "/docs",
        "endpoints": {
            "diagnose": "/api/v1/diagnose",
            "health": "/health",
        },
    }


@app.get("/health")
def health():
    return {"status": "healthy", "service": "agent-engine"}

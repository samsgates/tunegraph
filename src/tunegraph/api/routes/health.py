from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from tunegraph import __version__
from tunegraph.api.deps import SessionDep
from tunegraph.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=HealthResponse)
async def liveness(session: SessionDep) -> HealthResponse:
    try:
        await session.execute(text("SELECT 1"))
        database = "ok"
        status = "ok"
    except Exception:
        database = "unavailable"
        status = "degraded"
    return HealthResponse(status=status, version=__version__, database=database)


@router.get("/health/ready", response_model=HealthResponse)
async def readiness(session: SessionDep) -> HealthResponse:
    await session.execute(text("SELECT 1"))
    return HealthResponse(status="ok", version=__version__, database="ok")

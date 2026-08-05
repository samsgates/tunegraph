from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import ORJSONResponse

from tunegraph import __version__
from tunegraph.api.errors import TuneGraphError, tunegraph_error_handler
from tunegraph.api.router import api_router, root_router
from tunegraph.config import get_settings
from tunegraph.db.session import create_all_for_development
from tunegraph.logging import configure_logging
from tunegraph.observability import PrometheusMiddleware, configure_optional_otel, metrics_response

settings = get_settings()
configure_logging(settings)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    if settings.environment in {"development", "test"}:
        await create_all_for_development()
    logger.info("application_started", version=__version__, environment=settings.environment)
    yield
    logger.info("application_stopped")


app = FastAPI(
    title="TuneGraph API",
    version=__version__,
    description="Control plane for traceable, composable, and reversible PEFT behavior",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(PrometheusMiddleware)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.trusted_hosts,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):  # type: ignore[no-untyped-def]
    request_id = request.headers.get("X-Request-ID") or "req_" + uuid.uuid4().hex
    request.state.request_id = request_id
    structlog.contextvars.bind_contextvars(request_id=request_id)
    try:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > settings.max_request_bytes:
            return ORJSONResponse(
                status_code=413,
                content={"error": {"code": "REQUEST_TOO_LARGE", "request_id": request_id}},
            )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
    finally:
        structlog.contextvars.clear_contextvars()


app.add_exception_handler(TuneGraphError, tunegraph_error_handler)  # type: ignore[arg-type]
app.include_router(api_router, prefix=settings.api_prefix)
app.include_router(root_router)
configure_optional_otel(app, settings)


@app.get("/metrics", include_in_schema=False)
async def metrics():  # type: ignore[no-untyped-def]
    return metrics_response()


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"name": "TuneGraph", "version": __version__, "status": "ok"}

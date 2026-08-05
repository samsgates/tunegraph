from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import ORJSONResponse


class TuneGraphError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


async def tunegraph_error_handler(request: Request, exc: TuneGraphError) -> ORJSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return ORJSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id,
                "details": exc.details,
            }
        },
    )

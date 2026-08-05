from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from tunegraph.api.context import Principal
from tunegraph.api.deps import SessionDep, SettingsDep, require_permission
from tunegraph.schemas import ChatCompletionRequest
from tunegraph.services.inference import InferenceService

router = APIRouter(tags=["inference"])


@router.post("/v1/chat/completions")
async def chat_completions(
    payload: ChatCompletionRequest,
    session: SessionDep,
    settings: SettingsDep,
    principal: Principal = Depends(require_permission("inference:invoke")),
) -> dict[str, Any]:
    service = InferenceService(settings)
    response, _ = await service.invoke(session, principal, payload)
    return response

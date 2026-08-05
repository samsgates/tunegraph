from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tunegraph.api.context import Principal
from tunegraph.config import Settings, get_settings
from tunegraph.db.models import APIKey, User
from tunegraph.db.session import get_session
from tunegraph.domain.enums import Role
from tunegraph.domain.permissions import has_permission
from tunegraph.security.tokens import decode_token, hash_api_key

bearer = HTTPBearer(auto_error=False)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


async def get_principal(
    session: SessionDep,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> Principal:
    if x_api_key:
        digest = hash_api_key(x_api_key)
        api_key = (
            await session.execute(select(APIKey).where(APIKey.key_hash == digest))
        ).scalar_one_or_none()
        now = datetime.now(UTC)
        if (
            api_key is None
            or api_key.revoked_at is not None
            or (api_key.expires_at is not None and api_key.expires_at <= now)
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        api_key.last_used_at = now
        await session.commit()
        return Principal(
            subject=api_key.owner_user_id or api_key.id,
            organization_id=api_key.organization_id,
            roles=frozenset(Role(role) for role in api_key.roles),
            auth_type="api_key",
        )

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = decode_token(settings, credentials.credentials, "access")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    user = await session.get(User, str(payload["sub"]))
    if user is None or not user.is_active or user.organization_id != payload["org"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive")
    return Principal(
        subject=user.id,
        organization_id=user.organization_id,
        roles=frozenset(Role(role) for role in user.roles),
        auth_type="user",
    )


PrincipalDep = Annotated[Principal, Depends(get_principal)]


def require_permission(permission: str) -> Callable[[PrincipalDep], Principal]:
    async def dependency(principal: PrincipalDep) -> Principal:
        if not has_permission(set(principal.roles), permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return principal

    return dependency


def request_id(request: Request) -> str:
    return str(request.state.request_id)

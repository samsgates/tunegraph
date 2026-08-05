from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from tunegraph.api.context import Principal
from tunegraph.api.deps import PrincipalDep, SessionDep, SettingsDep, require_permission
from tunegraph.db.models import APIKey, Organization, User
from tunegraph.schemas import (
    APIKeyCreate,
    APIKeyCreated,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UserCreate,
    UserRead,
)
from tunegraph.security.passwords import hash_password, verify_password
from tunegraph.security.tokens import create_token, decode_token, generate_api_key
from tunegraph.services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: SessionDep, settings: SettingsDep) -> TokenResponse:
    user = (
        await session.execute(
            select(User)
            .join(Organization, Organization.id == User.organization_id)
            .where(
                Organization.slug == payload.organization_slug,
                Organization.is_active.is_(True),
                User.email == payload.email.lower(),
            )
        )
    ).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    user.last_login_at = datetime.now(UTC)
    access, expires_in = create_token(
        settings=settings,
        subject=user.id,
        organization_id=user.organization_id,
        roles=user.roles,
        token_type="access",
    )
    refresh, _ = create_token(
        settings=settings,
        subject=user.id,
        organization_id=user.organization_id,
        roles=user.roles,
        token_type="refresh",
    )
    await session.commit()
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=expires_in)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, session: SessionDep, settings: SettingsDep) -> TokenResponse:
    try:
        claims = decode_token(settings, payload.refresh_token, "refresh")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    user = await session.get(User, str(claims["sub"]))
    if (
        user is None
        or not user.is_active
        or user.organization_id != str(claims["org"])
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive")
    access, expires_in = create_token(
        settings=settings,
        subject=user.id,
        organization_id=user.organization_id,
        roles=user.roles,
        token_type="access",
    )
    refresh_token, _ = create_token(
        settings=settings,
        subject=user.id,
        organization_id=user.organization_id,
        roles=user.roles,
        token_type="refresh",
    )
    return TokenResponse(
        access_token=access,
        refresh_token=refresh_token,
        expires_in=expires_in,
    )


@router.get("/me", response_model=UserRead)
async def me(principal: PrincipalDep, session: SessionDep) -> User:
    user = await session.get(User, principal.subject)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/users", response_model=UserRead, status_code=201)
async def create_user(
    payload: UserCreate,
    session: SessionDep,
    principal: Principal = Depends(require_permission("users:*")),
) -> User:
    existing = (
        await session.execute(
            select(User).where(
                User.organization_id == principal.organization_id,
                User.email == payload.email.lower(),
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    user = User(
        organization_id=principal.organization_id,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        roles=[role.value for role in payload.roles],
    )
    session.add(user)
    await session.flush()
    await record_audit(
        session,
        action="user.created",
        resource_type="user",
        resource_id=user.id,
        principal=principal,
        after_state={"email": user.email, "roles": user.roles},
    )
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/api-keys", response_model=APIKeyCreated, status_code=201)
async def create_api_key(
    payload: APIKeyCreate,
    session: SessionDep,
    principal: Principal = Depends(require_permission("users:*")),
) -> APIKeyCreated:
    raw, prefix, digest = generate_api_key()
    key = APIKey(
        organization_id=principal.organization_id,
        owner_user_id=principal.subject if principal.auth_type == "user" else None,
        name=payload.name,
        key_prefix=prefix,
        key_hash=digest,
        roles=[role.value for role in payload.roles],
        expires_at=payload.expires_at,
    )
    session.add(key)
    await session.flush()
    await record_audit(
        session,
        action="api_key.created",
        resource_type="api_key",
        resource_id=key.id,
        principal=principal,
        after_state={"name": key.name, "prefix": prefix, "roles": key.roles},
    )
    await session.commit()
    return APIKeyCreated(
        id=key.id,
        name=key.name,
        key=raw,
        key_prefix=prefix,
        expires_at=key.expires_at,
    )

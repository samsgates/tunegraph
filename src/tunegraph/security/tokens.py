from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from jwt import InvalidTokenError

from tunegraph.config import Settings

TokenType = Literal["access", "refresh"]


def create_token(
    *,
    settings: Settings,
    subject: str,
    organization_id: str,
    roles: list[str],
    token_type: TokenType,
) -> tuple[str, int]:
    now = datetime.now(UTC)
    lifetime = (
        timedelta(minutes=settings.access_token_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_days)
    )
    expires = now + lifetime
    payload: dict[str, Any] = {
        "sub": subject,
        "org": organization_id,
        "roles": roles,
        "typ": token_type,
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "jti": secrets.token_urlsafe(16),
        "iss": "tunegraph",
        "aud": "tunegraph-api",
    }
    token = jwt.encode(payload, settings.secret_key.get_secret_value(), algorithm="HS256")
    return token, int(lifetime.total_seconds())


def decode_token(settings: Settings, token: str, expected_type: TokenType) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=["HS256"],
            audience="tunegraph-api",
            issuer="tunegraph",
            options={"require": ["exp", "iat", "nbf", "sub", "org", "typ"]},
        )
    except InvalidTokenError as exc:
        raise ValueError("Invalid or expired token") from exc
    if payload.get("typ") != expected_type:
        raise ValueError("Incorrect token type")
    return payload


def generate_api_key() -> tuple[str, str, str]:
    raw = "tg_" + secrets.token_urlsafe(32)
    prefix = raw[:12]
    digest = hashlib.sha256(raw.encode()).hexdigest()
    return raw, prefix, digest


def hash_api_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()

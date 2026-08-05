from pathlib import Path

from tunegraph.config import Settings
from tunegraph.security.passwords import hash_password, verify_password
from tunegraph.security.signing import generate_keypair, sign_bytes, verify_bytes
from tunegraph.security.tokens import create_token, decode_token, generate_api_key, hash_api_key


def test_password_hash_round_trip() -> None:
    hashed = hash_password("a-strong-test-password")
    assert verify_password("a-strong-test-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_token_round_trip() -> None:
    settings = Settings(secret_key="x" * 64)
    token, expires = create_token(
        settings=settings,
        subject="user-1",
        organization_id="org-1",
        roles=["platform_admin"],
        token_type="access",
    )
    claims = decode_token(settings, token, "access")
    assert claims["sub"] == "user-1"
    assert claims["org"] == "org-1"
    assert expires > 0


def test_api_key_is_only_stored_as_hash() -> None:
    raw, prefix, digest = generate_api_key()
    assert raw.startswith("tg_")
    assert prefix == raw[:12]
    assert digest == hash_api_key(raw)
    assert raw not in digest


def test_ed25519_signature(tmp_path: Path) -> None:
    private = tmp_path / "private.pem"
    public = tmp_path / "public.pem"
    generate_keypair(private, public)
    payload = b"immutable manifest"
    signature = sign_bytes(private, payload)
    assert verify_bytes(public, payload, signature)
    assert not verify_bytes(public, b"modified manifest", signature)


def test_production_configuration_requires_existing_signing_keys(tmp_path: Path) -> None:
    settings = Settings(
        environment="production",
        database_url="postgresql+psycopg://user:password@db/tunegraph",
        secret_key="x" * 64,
        signing_public_key_path=tmp_path / "missing-public.pem",
        signing_private_key_path=tmp_path / "missing-private.pem",
    )
    try:
        settings.validate_production_safety()
    except RuntimeError as exc:
        assert "public key" in str(exc)
    else:
        raise AssertionError("Production safety validation should reject missing keys")

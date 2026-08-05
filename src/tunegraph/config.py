from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TUNEGRAPH_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "TuneGraph"
    environment: Literal["development", "test", "staging", "production"] = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite+aiosqlite:///./tunegraph.db"
    secret_key: SecretStr = SecretStr("development-secret-change-before-production")
    access_token_minutes: int = 30
    refresh_token_days: int = 7
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: SecretStr | None = None

    artifact_root: Path = Path("./var/artifacts")
    inference_backend_url: str = "http://localhost:8001"
    inference_backend_api_key: SecretStr | None = None
    inference_timeout_seconds: float = 120.0
    opa_url: str | None = None
    opa_timeout_seconds: float = 2.0

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    trusted_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1", "testserver"]
    )
    allowed_artifact_schemes: list[str] = Field(
        default_factory=lambda: ["file", "s3", "oci"]
    )
    max_request_bytes: int = 2 * 1024 * 1024
    max_page_size: int = 200
    default_page_size: int = 50

    otel_exporter_otlp_endpoint: str | None = None
    log_level: str = "INFO"
    json_logs: bool = True

    signing_private_key_path: Path | None = None
    signing_public_key_path: Path | None = None
    allow_unsigned_artifacts: bool = False

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("secret_key must contain at least 32 characters")
        return value

    @field_validator("artifact_root")
    @classmethod
    def normalize_artifact_root(cls, value: Path) -> Path:
        return value.expanduser().resolve()

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def validate_production_safety(self) -> None:
        if not self.is_production:
            return
        if "change-before-production" in self.secret_key.get_secret_value():
            raise RuntimeError("Refusing to start production with the development secret key")
        if self.database_url.startswith("sqlite"):
            raise RuntimeError("Production requires PostgreSQL, SQLite is development-only")
        if self.allow_unsigned_artifacts:
            raise RuntimeError("Unsigned artifacts cannot be enabled in production")
        if not self.signing_public_key_path:
            raise RuntimeError("Production requires TUNEGRAPH_SIGNING_PUBLIC_KEY_PATH")
        if not self.signing_public_key_path.is_file():
            raise RuntimeError("The configured signing public key does not exist")
        if not self.signing_private_key_path:
            raise RuntimeError("Production requires TUNEGRAPH_SIGNING_PRIVATE_KEY_PATH")
        if not self.signing_private_key_path.is_file():
            raise RuntimeError("The configured signing private key does not exist")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_production_safety()
    settings.artifact_root.mkdir(parents=True, exist_ok=True)
    return settings

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer

from tunegraph import __version__
from tunegraph.config import get_settings
from tunegraph.db.session import SessionLocal, create_all_for_development
from tunegraph.security.signing import generate_keypair
from tunegraph.services.bootstrap import bootstrap_admin

app = typer.Typer(help="TuneGraph management CLI", no_args_is_help=True)
keys_app = typer.Typer(help="Artifact-signing key operations")
app.add_typer(keys_app, name="keys")


def version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=version_callback, is_eager=True, help="Show version"),
    ] = None,
) -> None:
    del version


@app.command()
def doctor() -> None:
    """Validate local configuration and print a safe summary."""
    settings = get_settings()
    checks = {
        "environment": settings.environment,
        "database_driver": settings.database_url.split(":", 1)[0],
        "artifact_root": str(settings.artifact_root),
        "artifact_root_exists": settings.artifact_root.exists(),
        "inference_backend_url": settings.inference_backend_url,
        "opa_enabled": bool(settings.opa_url),
        "signing_enabled": bool(settings.signing_public_key_path),
    }
    typer.echo(json.dumps(checks, indent=2))


@app.command()
def bootstrap(
    email: Annotated[str | None, typer.Option(help="Initial administrator email")] = None,
    password: Annotated[
        str | None, typer.Option(help="Initial administrator password", prompt=True, hide_input=True)
    ] = None,
    organization: Annotated[str, typer.Option(help="Organization name")] = "Default Organization",
    slug: Annotated[str, typer.Option(help="Organization slug")] = "default",
) -> None:
    """Create the first organization and platform administrator."""
    settings = get_settings()
    resolved_email = email or settings.bootstrap_admin_email
    resolved_password = password or (
        settings.bootstrap_admin_password.get_secret_value()
        if settings.bootstrap_admin_password
        else None
    )
    if not resolved_email or not resolved_password:
        raise typer.BadParameter("Email and password are required")
    if len(resolved_password) < 12:
        raise typer.BadParameter("Password must contain at least 12 characters")

    async def run() -> None:
        if settings.environment in {"development", "test"}:
            await create_all_for_development()
        async with SessionLocal() as session:
            org, user, created = await bootstrap_admin(
                session,
                email=resolved_email,
                password=resolved_password,
                organization_name=organization,
                organization_slug=slug,
            )
            typer.echo(
                json.dumps(
                    {
                        "organization_id": org.id,
                        "user_id": user.id,
                        "email": user.email,
                        "created": created,
                    },
                    indent=2,
                )
            )

    asyncio.run(run())


@keys_app.command("generate")
def generate_keys(
    private_key: Annotated[Path, typer.Option(help="Private key path")] = Path(
        "./var/keys/tunegraph-private.pem"
    ),
    public_key: Annotated[Path, typer.Option(help="Public key path")] = Path(
        "./var/keys/tunegraph-public.pem"
    ),
) -> None:
    """Generate an Ed25519 signing key pair."""
    if private_key.exists() or public_key.exists():
        raise typer.BadParameter("Refusing to overwrite an existing key")
    generate_keypair(private_key.resolve(), public_key.resolve())
    typer.echo(f"Private key: {private_key.resolve()}")
    typer.echo(f"Public key: {public_key.resolve()}")


if __name__ == "__main__":
    app()

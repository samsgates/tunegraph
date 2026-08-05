from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tunegraph.db.models import Organization, User
from tunegraph.domain.enums import Role
from tunegraph.security.passwords import hash_password


async def bootstrap_admin(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    organization_name: str = "Default Organization",
    organization_slug: str = "default",
) -> tuple[Organization, User, bool]:
    organization = (
        await session.execute(select(Organization).where(Organization.slug == organization_slug))
    ).scalar_one_or_none()
    created = False
    if organization is None:
        organization = Organization(name=organization_name, slug=organization_slug)
        session.add(organization)
        await session.flush()
        created = True

    user = (
        await session.execute(
            select(User).where(
                User.organization_id == organization.id,
                User.email == email.lower(),
            )
        )
    ).scalar_one_or_none()
    if user is None:
        user = User(
            organization_id=organization.id,
            email=email.lower(),
            password_hash=hash_password(password),
            full_name="Platform Administrator",
            roles=[Role.PLATFORM_ADMIN.value],
        )
        session.add(user)
        created = True
    await session.commit()
    await session.refresh(organization)
    await session.refresh(user)
    return organization, user, created

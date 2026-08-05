from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from tunegraph.api.context import Principal
from tunegraph.db.models import AuditEvent


async def record_audit(
    session: AsyncSession,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None,
    principal: Principal | None,
    request_id: str | None = None,
    source_ip: str | None = None,
    before_state: dict[str, Any] | None = None,
    after_state: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        organization_id=principal.organization_id if principal else None,
        actor_id=principal.subject if principal else None,
        actor_type=principal.auth_type if principal else "system",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        source_ip=source_ip,
        before_state=before_state or {},
        after_state=after_state or {},
        event_metadata=metadata or {},
        created_at=datetime.now(UTC),
    )
    session.add(event)
    return event

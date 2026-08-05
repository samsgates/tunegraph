from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select

from tunegraph.api.context import Principal
from tunegraph.api.deps import SessionDep, require_permission
from tunegraph.db.models import AuditEvent

router = APIRouter(prefix="/audit-events", tags=["audit"])


@router.get("")
async def list_audit_events(
    session: SessionDep,
    principal: Principal = Depends(require_permission("audit:read")),
) -> list[dict[str, object]]:
    events = (
        await session.execute(
            select(AuditEvent)
            .where(AuditEvent.organization_id == principal.organization_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(500)
        )
    ).scalars().all()
    return [
        {
            "id": event.id,
            "action": event.action,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "actor_id": event.actor_id,
            "created_at": event.created_at.isoformat(),
            "before_state": event.before_state,
            "after_state": event.after_state,
            "metadata": event.event_metadata,
        }
        for event in events
    ]

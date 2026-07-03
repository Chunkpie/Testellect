import json
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.admin import AuditLog


async def log_audit_entry(
    db: AsyncSession,
    user_id: int,
    school_id: Optional[int] = None,
    action: str = "",
    resource_type: str = "",
    resource_id: Optional[int] = None,
    extra_data: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        school_id=school_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        meta_data=json.dumps(extra_data) if extra_data else None,
        ip_address=ip_address,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry

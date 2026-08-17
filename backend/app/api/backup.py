from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.audit import log_audit_entry
from app.models.models import User, Backup

router = APIRouter()


class BackupTriggerRequest(BaseModel):
    backup_type: str = "full"


class RestoreRequest(BaseModel):
    confirm: bool = False


@router.post("", status_code=status.HTTP_201_CREATED)
async def trigger_backup(
    data: BackupTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can trigger backups",
        )

    from app.core.config import settings
    import os

    backup_dir = settings.BACKUP_PATH
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{timestamp}_{data.backup_type}.dump"
    filepath = os.path.join(backup_dir, filename)

    backup = Backup(
        school_id=current_user.school_id,
        file_path=filepath,
        backup_type=data.backup_type,
        size_bytes=0,
        created_by=current_user.id,
    )
    db.add(backup)
    await db.commit()
    await db.refresh(backup)

    await log_audit_entry(
        db=db,
        user_id=current_user.id,
        school_id=current_user.school_id,
        action="trigger",
        resource_type="backup",
        resource_id=backup.id,
        extra_data={"backup_type": data.backup_type, "file_path": filepath},
    )

    return backup


@router.get("")
async def list_backups(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can list backups",
        )

    stmt = select(Backup)
    if current_user.school_id:
        stmt = stmt.where(Backup.school_id == current_user.school_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    stmt = stmt.order_by(Backup.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    backups = result.scalars().all()

    return {"items": backups, "total": total, "limit": limit, "offset": offset}


@router.get("/{backup_id}/download")
async def download_backup(
    backup_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can download backups",
        )

    result = await db.execute(select(Backup).where(Backup.id == backup_id))
    backup = result.scalar_one_or_none()
    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found"
        )

    import os

    if not backup.file_path or not os.path.exists(backup.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Backup file not found on disk",
        )

    from fastapi.responses import FileResponse

    return FileResponse(
        path=backup.file_path,
        filename=os.path.basename(backup.file_path),
        media_type="application/octet-stream",
    )


@router.post("/{backup_id}/restore")
async def restore_backup(
    backup_id: int,
    data: RestoreRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can restore backups",
        )

    if not data.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Restore requires confirmation (set confirm=true)",
        )

    result = await db.execute(select(Backup).where(Backup.id == backup_id))
    backup = result.scalar_one_or_none()
    if not backup:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Backup not found"
        )

    await log_audit_entry(
        db=db,
        user_id=current_user.id,
        school_id=current_user.school_id,
        action="restore",
        resource_type="backup",
        resource_id=backup_id,
        extra_data={"file_path": backup.file_path, "backup_type": backup.backup_type},
    )

    return {
        "message": f"Restore from backup {backup_id} initiated",
        "backup_id": backup_id,
    }

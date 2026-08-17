import os
import uuid
import shutil
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.db.models.auth import User
from app.db.models.image_bank import ImageAsset
from app.core.config import settings

router = APIRouter()

# Ensure uploads directory exists
UPLOAD_DIR = os.path.join(settings.FILE_STORAGE_PATH, "images")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    tags: str = Form(""),
    subject_id: Optional[int] = Form(None),
    grade_range_min: Optional[int] = Form(None),
    grade_range_max: Optional[int] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "administrator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can upload images",
        )

    # Validate MIME type
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image format (must be JPEG, PNG, or WebP)",
        )

    # Validate file size (max 5MB)
    MAX_FILE_SIZE = 5 * 1024 * 1024

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 5MB.",
        )

    # Generate safe filename
    ext = os.path.splitext(file.filename)[1]
    if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image extension"
        )

    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    relative_path = f"/storage/images/{unique_filename}"

    asset = ImageAsset(
        school_id=current_user.school_id,
        file_path=relative_path,
        tags=tags.lower(),
        subject_id=subject_id,
        grade_range_min=grade_range_min,
        grade_range_max=grade_range_max,
        uploaded_by=current_user.id,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)

    return {
        "id": asset.id,
        "file_path": asset.file_path,
        "tags": asset.tags,
        "message": "Image uploaded successfully",
    }


@router.get("")
async def list_images(
    tags: Optional[str] = None,
    subject_id: Optional[int] = None,
    grade: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(ImageAsset)
    if current_user.role not in ("administrator", "deo"):
        stmt = stmt.where(ImageAsset.school_id == current_user.school_id)

    if tags:
        tag_list = [t.strip().lower() for t in tags.split(",") if t.strip()]
        for t in tag_list:
            stmt = stmt.where(ImageAsset.tags.ilike(f"%{t}%"))

    if subject_id:
        stmt = stmt.where(ImageAsset.subject_id == subject_id)

    if grade:
        stmt = stmt.where(
            ImageAsset.grade_range_min <= grade, ImageAsset.grade_range_max >= grade
        )

    result = await db.execute(stmt)
    images = result.scalars().all()

    return {
        "items": [
            {
                "id": img.id,
                "file_path": img.file_path,
                "tags": img.tags,
                "subject_id": img.subject_id,
                "grade_range_min": img.grade_range_min,
                "grade_range_max": img.grade_range_max,
                "created_at": img.created_at.isoformat() if img.created_at else None,
            }
            for img in images
        ],
        "total": len(images),
    }


@router.delete("/{asset_id}")
async def delete_image(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(ImageAsset).where(ImageAsset.id == asset_id))
    asset = result.scalar_one_or_none()

    if not asset:
        raise HTTPException(status_code=404, detail="Image not found")

    if (
        current_user.role not in ("administrator", "deo")
        and asset.school_id != current_user.school_id
    ):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Optional: Delete file from disk
    # ...

    await db.delete(asset)
    await db.commit()
    return {"message": "Image deleted"}

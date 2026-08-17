import json
import random

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.audit import log_audit_entry
from app.models.models import User, Blueprint, Paper, Subject
from app.schemas.papers import BlueprintCreate, BlueprintResponse

router = APIRouter()


def _school_scope_filter(model, user):
    if user.role in ("administrator", "deo"):
        return None
    return model.school_id == user.school_id


def _validate_distributions(data: BlueprintCreate):
    errors = []

    if data.difficulty_distribution:
        try:
            dist = json.loads(data.difficulty_distribution)
            total_pct = sum(dist.values())
            if abs(total_pct - 100) > 1:
                errors.append(
                    f"Difficulty distribution sums to {total_pct}%, expected 100%"
                )
        except (json.JSONDecodeError, TypeError):
            errors.append("Invalid difficulty_distribution JSON")

    if data.bloom_distribution:
        try:
            dist = json.loads(data.bloom_distribution)
            total_pct = sum(dist.values())
            if abs(total_pct - 100) > 1:
                errors.append(f"Bloom distribution sums to {total_pct}%, expected 100%")
        except (json.JSONDecodeError, TypeError):
            errors.append("Invalid bloom_distribution JSON")

    if data.competency_distribution:
        try:
            dist = json.loads(data.competency_distribution)
            total_pct = sum(dist.values())
            if abs(total_pct - 100) > 1:
                errors.append(
                    f"Competency distribution sums to {total_pct}%, expected 100%"
                )
        except (json.JSONDecodeError, TypeError):
            errors.append("Invalid competency_distribution JSON")

    return errors


@router.get("")
async def list_blueprints(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "administrator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    stmt = select(Blueprint)
    scope = _school_scope_filter(Blueprint, current_user)
    if scope is not None:
        stmt = stmt.where(scope)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    stmt = stmt.order_by(Blueprint.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    blueprints = result.scalars().all()

    return {"items": blueprints, "total": total, "limit": limit, "offset": offset}


@router.get("/{blueprint_id}")
async def get_blueprint(
    blueprint_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "administrator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    result = await db.execute(select(Blueprint).where(Blueprint.id == blueprint_id))
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found"
        )

    return bp


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_blueprint(
    data: BlueprintCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "administrator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and administrators can create blueprints",
        )

    errors = _validate_distributions(data)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors
        )

    bp_data = data.model_dump()
    bp_data["created_by"] = current_user.id
    bp = Blueprint(**bp_data)
    db.add(bp)
    await db.commit()
    await db.refresh(bp)

    await log_audit_entry(
        db=db,
        user_id=current_user.id,
        school_id=bp.school_id,
        action="create",
        resource_type="blueprint",
        resource_id=bp.id,
    )

    return bp


@router.patch("/{blueprint_id}")
async def update_blueprint(
    blueprint_id: int,
    data: BlueprintCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "administrator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and administrators can update blueprints",
        )

    result = await db.execute(select(Blueprint).where(Blueprint.id == blueprint_id))
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found"
        )

    paper_result = await db.execute(
        select(Paper).where(Paper.blueprint_id == blueprint_id).limit(1)
    )
    if paper_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update blueprint after papers have been generated",
        )

    errors = _validate_distributions(data)
    if errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=errors
        )

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(bp, key, val)

    await db.commit()
    await db.refresh(bp)

    await log_audit_entry(
        db=db,
        user_id=current_user.id,
        school_id=bp.school_id,
        action="update",
        resource_type="blueprint",
        resource_id=bp.id,
    )

    return bp


class CoverageRequest(BaseModel):
    chapter_ids: list[int] | None = None
    difficulty_distribution: dict[str, float] | None = None
    bloom_distribution: dict[str, float] | None = None
    competency_distribution: dict[str, float] | None = None


@router.post("/{blueprint_id}/check-coverage")
async def check_coverage(
    blueprint_id: int,
    data: CoverageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "administrator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and administrators can check coverage",
        )

    result = await db.execute(select(Blueprint).where(Blueprint.id == blueprint_id))
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found"
        )

    from app.models.models import QuestionBank

    stmt = select(func.count()).select_from(QuestionBank)
    stmt = stmt.where(QuestionBank.school_id == bp.school_id)
    stmt = stmt.where(QuestionBank.is_deleted == False)

    if data.chapter_ids:
        from app.models.models import Concept

        chapter_concepts = await db.execute(
            select(Concept.id).where(Concept.chapter_id.in_(data.chapter_ids))
        )
        concept_ids = [r for r in chapter_concepts.scalars()]
        if concept_ids:
            stmt = stmt.where(QuestionBank.concept_id.in_(concept_ids))

    total_result = await db.execute(stmt)
    available = total_result.scalar()

    shortfalls = {}
    if data.difficulty_distribution:
        for level, pct in data.difficulty_distribution.items():
            needed = int(pct / 100 * bp.total_questions)
            cnt_result = await db.execute(
                select(func.count())
                .select_from(QuestionBank)
                .where(QuestionBank.difficulty == level)
                .where(QuestionBank.school_id == bp.school_id)
                .where(QuestionBank.is_deleted == False)
            )
            have = cnt_result.scalar()
            if have < needed:
                shortfalls[f"difficulty:{level}"] = needed - have

    return {
        "blueprint_id": blueprint_id,
        "questions_available": available,
        "total_required": bp.total_questions,
        "shortfalls": shortfalls,
        "coverage_ok": len(shortfalls) == 0,
    }


@router.post("/{blueprint_id}/generate", status_code=status.HTTP_201_CREATED)
async def generate_paper_from_blueprint(
    blueprint_id: int,
    req: dict,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timezone
    from app.core.constants import ApprovalStatus
    from app.db.models.questions import QuestionBank

    if user.role not in ("teacher", "administrator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers and administrators can generate papers",
        )

    result = await db.execute(select(Blueprint).where(Blueprint.id == blueprint_id))
    blueprint = result.scalar_one_or_none()
    if not blueprint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found"
        )

    scope = _school_scope_filter(Blueprint, user)
    if scope is not None and blueprint.school_id != user.school_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    try:
        bloom_dist = (
            json.loads(blueprint.bloom_distribution)
            if blueprint.bloom_distribution
            else {}
        )
        difficulty_dist = (
            json.loads(blueprint.difficulty_distribution)
            if blueprint.difficulty_distribution
            else {}
        )
    except (json.JSONDecodeError, TypeError):
        bloom_dist = {}
        difficulty_dist = {}

    bloom_pool = (
        list(bloom_dist.keys())
        if bloom_dist
        else ["remember", "understand", "apply", "analyze", "evaluate"]
    )
    difficulty_pool = (
        list(difficulty_dist.keys()) if difficulty_dist else ["easy", "medium", "hard"]
    )

    from sqlalchemy import text

    q_stmt = select(QuestionBank).where(
        QuestionBank.approval_status == ApprovalStatus.APPROVED.value,
        QuestionBank.school_id == blueprint.school_id,
    )
    q_result = await db.execute(q_stmt)
    all_questions = q_result.scalars().all()

    if not all_questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No approved questions available",
        )

    selected: list[QuestionBank] = []
    remaining = blueprint.total_questions

    for bloom_level in bloom_pool:
        if remaining <= 0:
            break
        bloom_weight = (
            bloom_dist.get(bloom_level, 0) / 100.0
            if bloom_dist
            else 1.0 / len(bloom_pool)
        )
        target = max(1, int(blueprint.total_questions * bloom_weight))
        pool = [
            q
            for q in all_questions
            if q.bloom_level == bloom_level and q not in selected
        ]
        random.shuffle(pool)
        selected.extend(pool[:target])
        remaining -= target

    for diff in difficulty_pool:
        if remaining <= 0:
            break
        diff_weight = (
            difficulty_dist.get(diff, 0) / 100.0
            if difficulty_dist
            else 1.0 / len(difficulty_pool)
        )
        target = max(1, int(blueprint.total_questions * diff_weight))
        pool = [q for q in all_questions if q.difficulty == diff and q not in selected]
        random.shuffle(pool)
        selected.extend(pool[:target])
        remaining -= target

    if remaining > 0:
        random.shuffle(all_questions)
        for q in all_questions:
            if q not in selected:
                selected.append(q)
                remaining -= 1
                if remaining <= 0:
                    break

    selected = selected[: blueprint.total_questions]
    random.shuffle(selected)

    paper_name = req.get("name") if isinstance(req, dict) else None
    paper = Paper(
        blueprint_id=blueprint.id,
        variant_label=paper_name or blueprint.name,
        generated_at=datetime.now(timezone.utc),
        generated_by=user.id,
    )
    db.add(paper)
    await db.flush()

    from app.db.models.papers import PaperQuestion

    for i, q in enumerate(selected):
        pq = PaperQuestion(
            paper_id=paper.id,
            question_id=q.id,
            sequence=i + 1,
        )
        db.add(pq)

    paper.pdf_file_path = f"reports/paper_{paper.id}.pdf"
    await db.commit()
    await db.refresh(paper)

    await log_audit_entry(
        db=db,
        user_id=user.id,
        school_id=blueprint.school_id,
        action="generate",
        resource_type="paper",
        resource_id=paper.id,
    )

    return {
        "paper_id": paper.id,
        "name": paper.variant_label,
        "total_questions": len(selected),
        "total_marks": float(blueprint.total_marks),
        "blueprint_id": blueprint.id,
    }


@router.delete("/{blueprint_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blueprint(
    blueprint_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("teacher", "administrator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions"
        )

    result = await db.execute(select(Blueprint).where(Blueprint.id == blueprint_id))
    bp = result.scalar_one_or_none()
    if not bp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Blueprint not found"
        )

    paper_result = await db.execute(
        select(Paper).where(Paper.blueprint_id == blueprint_id).limit(1)
    )
    if paper_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete blueprint that has generated papers",
        )

    await db.delete(bp)
    await db.commit()

    await log_audit_entry(
        db=db,
        user_id=current_user.id,
        school_id=bp.school_id,
        action="delete",
        resource_type="blueprint",
        resource_id=blueprint_id,
    )

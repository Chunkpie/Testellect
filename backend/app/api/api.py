from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.chapters import router as chapters_router
from app.api.questions import router as questions_router
from app.api.papers import router as papers_router
from app.api.omr import router as omr_router
from app.api.analytics import router as analytics_router
from app.api.reports import router as reports_router
from app.api.jobs import router as jobs_router
from app.api.dashboard import router as dashboard_router
from app.api.schools import router as schools_router
from app.api.students import router as students_router
from app.api.subjects import router as subjects_router
from app.api.blueprints import router as blueprints_router
from app.api.assessments import router as assessments_router
from app.api.backup import router as backup_router
from app.api.audit import router as audit_router
from app.api.knowledge_base import router as knowledge_base_router
from app.api.ai import router as ai_router
from app.api.export import router as export_router
from app.api.image_bank import router as image_bank_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router, prefix="/auth", tags=["Auth"])
router.include_router(chapters_router, prefix="/chapters", tags=["Chapters"])
router.include_router(questions_router, prefix="/questions", tags=["Questions"])
router.include_router(papers_router, prefix="/papers", tags=["Papers"])
router.include_router(omr_router, prefix="/omr", tags=["OMR"])
router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
router.include_router(reports_router, prefix="/reports", tags=["Reports"])
router.include_router(jobs_router, prefix="/jobs", tags=["Jobs"])
router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
router.include_router(schools_router, prefix="/schools", tags=["Schools"])
router.include_router(students_router, prefix="", tags=["Students & Classes"])
router.include_router(subjects_router, prefix="/subjects", tags=["Subjects"])
router.include_router(blueprints_router, prefix="/blueprints", tags=["Blueprints"])
router.include_router(assessments_router, prefix="/assessments", tags=["Assessments"])
router.include_router(backup_router, prefix="/backup", tags=["Backup"])
router.include_router(audit_router, prefix="/audit-logs", tags=["Audit"])
router.include_router(
    knowledge_base_router, prefix="/knowledge-base", tags=["Knowledge Base"]
)
router.include_router(ai_router, prefix="/ai", tags=["AI"])
router.include_router(export_router, prefix="/export", tags=["Export"])
router.include_router(image_bank_router, prefix="/image-bank", tags=["Image Bank"])

from app.api.mcq_engine import router as mcq_engine_router
from app.api.whatsapp_routes import router as whatsapp_router

router.include_router(
    mcq_engine_router, prefix="/mcq-engine", tags=["MCQ Engine & OMR"]
)
router.include_router(whatsapp_router)

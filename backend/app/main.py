import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import engine, Base
from app.core.errors import register_error_handlers
from app.api.api import router as api_router
from app.seed import seed_demo_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_warmup_task: asyncio.Task | None = None


async def _warmup_ollama():
    if settings.AI_PROVIDER_MODE.lower() == "cloud":
        logger.info("Cloud AI mode enabled. Skipping Ollama warmup.")
        return
    try:
        from app.services.ai_pipeline.ollama_client import OllamaClient

        client = OllamaClient(timeout_seconds=900)
        
        # Task 2b/3c: Auto-pull models before warming up
        await client.pull_model("llama3.2")
        await client.pull_model("llama3.2:1b")
        await client.pull_model("nomic-embed-text")
        
        logger.info("Pre-warming model (timeout=%d)...", client.timeout_seconds)
        await client.generate(
            prompt="Reply with just the word 'ready'.",
            system="You are a helpful assistant. Be concise.",
        )
        logger.info("Ollama model warmed up successfully")
    except Exception as e:
        logger.warning("Ollama warmup failed (will load on first request): %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _warmup_task
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_demo_data()

    from app.db.models.admin import Job
    from sqlalchemy import select, or_
    from sqlalchemy.ext.asyncio import AsyncSession
    from app.core.database import async_session_factory

    async with async_session_factory() as cleanup_db:
        stale = await cleanup_db.execute(
            select(Job).where(
                or_(Job.status == "processing", Job.status == "queued"),
                Job.type == "question_generation",
            )
        )
        for job in stale.scalars().all():
            job.status = "failed"
            job.error = "Server restarted while this job was running"
            logger.info("Marked stale job %s as failed", job.id)
        await cleanup_db.commit()

    _warmup_task = asyncio.create_task(_warmup_ollama())
    yield
    if _warmup_task and not _warmup_task.done():
        _warmup_task.cancel()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Testellect Platform",
        version="1.0.0",
        docs_url="/docs",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )

    register_error_handlers(application)

    application.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
    application.mount("/reports", StaticFiles(directory="reports"), name="reports")

    application.include_router(api_router)

    @application.get("/health")
    async def health():
        return {
            "status": "ok",
            "app": (
                settings.APP_NAME
                if hasattr(settings, "APP_NAME")
                else "Testellect Platform"
            ),
        }

    @application.get("/health/ready")
    async def health_ready(request: Request):
        return {
            "status": "ready",
            "app": (
                settings.APP_NAME
                if hasattr(settings, "APP_NAME")
                else "Testellect Platform"
            ),
        }

    import os
    from fastapi.responses import FileResponse

    if os.path.isdir("dist"):
        application.mount("/assets", StaticFiles(directory="dist/assets"), name="assets")
        
        @application.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            # If the path is an API call that wasn't matched, let it 404 naturally
            if full_path.startswith("api/"):
                return {"detail": "Not Found"}
            # Otherwise, serve the React app
            return FileResponse("dist/index.html")
            
    return application


app = create_app()

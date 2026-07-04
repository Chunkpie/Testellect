import asyncio
from app.core.database import async_session_factory
from app.services.ai_pipeline.pipeline_orchestrator import PipelineOrchestrator

async def test():
    async with async_session_factory() as session:
        ai = PipelineOrchestrator()
        await ai.process_book(session, 3)

if __name__ == "__main__":
    asyncio.run(test())

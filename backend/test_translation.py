import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.core.config import settings
from app.services.translation_service import translate_paper_questions

engine = create_async_engine(settings.DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

async def test():
    async with SessionLocal() as db:
        print("Translating...")
        await translate_paper_questions(db, 18, 'hindi')
        await db.commit()
        print('DONE')

if __name__ == "__main__":
    asyncio.run(test())

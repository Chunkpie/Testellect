import asyncio
from app.core.database import async_session_factory
from app.services.ai_service import AiService

async def main():
    async with async_session_factory() as db:
        ai = AiService()
        await ai.generate_and_create_papers(
            db=db,
            book_id=1,
            user_id=1,
            school_id=1,
            total_questions=3, # Test with just 3 to see if it generates quickly
            num_papers=2,
            questions_per_paper=1
        )
        print("Done!")

if __name__ == "__main__":
    asyncio.run(main())

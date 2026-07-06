import sys
import asyncio
import os
import argparse

sys.path.append(os.path.join(os.path.dirname(__file__), "app"))
from app.core.database import async_session_factory
from app.services.ai_service import AiService

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("book_id", type=int)
    args = parser.parse_args()

    async with async_session_factory() as session:
        ai_service = AiService()
        await ai_service.analyze_book(session, args.book_id, user_id=None)

if __name__ == "__main__":
    asyncio.run(main())

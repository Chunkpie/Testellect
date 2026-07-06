import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session_factory
from app.api.papers import export_paper_pdf
from app.models.models import User
import sys

async def main():
    async with async_session_factory() as db:
        # Get a user (admin)
        from sqlalchemy import select
        res = await db.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        
        # Get a paper id
        from app.db.models.papers import Paper
        res = await db.execute(select(Paper).limit(1))
        paper = res.scalar_one_or_none()
        
        if not paper:
            print("No papers found")
            return
            
        try:
            resp = await export_paper_pdf(paper.id, "english", user, db)
            print(f"Response Type: {type(resp)}")
            print(f"Headers: {resp.headers}")
            print(f"Body Length: {len(resp.body)}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.models import User
from app.core.security import create_access_token
import httpx

async def main():
    async with async_session_factory() as db:
        res = await db.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        
        if not user:
            print("No users found")
            return
            
        token = create_access_token(data={"sub": str(user.id)})
        
        async with httpx.AsyncClient(base_url="http://localhost:8000/api/v1") as client:
            resp = await client.get("/papers/22/export?lang=hindi", headers={"Authorization": f"Bearer {token}"}, timeout=60.0)
            print(f"Status: {resp.status_code}")
            print(f"Headers: {resp.headers}")
            print(f"Length: {len(resp.content)}")
            if resp.status_code != 200:
                print(f"Body: {resp.text}")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.models import Class, Student

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@postgres:5432/parakh_db"

engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def seed_students():
    async with SessionLocal() as session:
        result = await session.execute(select(Class))
        classes = result.scalars().all()
        
        for c in classes:
            count_stmt = select(Student).where(Student.class_id == c.id)
            existing = (await session.execute(count_stmt)).scalars().all()
            if not existing:
                print(f"Adding students for Class ID {c.id}")
                for i in range(1, 11):
                    student = Student(
                        school_id=c.school_id,
                        class_id=c.id,
                        roll_number=f"R{c.id}-{i:03d}",
                        full_name=f"Student {i} (Class {c.id})",
                        is_active=True,
                        is_deleted=False
                    )
                    session.add(student)
        await session.commit()
        print("Students seeded successfully.")

asyncio.run(seed_students())

import asyncio
from app.db.session import async_session_maker
from app.db.models.questions import QuestionBank, QuestionOption
from app.db.models.papers import Blueprint, Paper, PaperQuestion, OMRSheet
from app.db.models.assessments import Assessment
from sqlalchemy import text

async def main():
    async with async_session_maker() as session:
        await session.execute(text('TRUNCATE TABLE omr_sheets CASCADE'))
        await session.execute(text('TRUNCATE TABLE paper_questions CASCADE'))
        await session.execute(text('TRUNCATE TABLE papers CASCADE'))
        await session.execute(text('TRUNCATE TABLE blueprints CASCADE'))
        await session.execute(text('TRUNCATE TABLE question_options CASCADE'))
        await session.execute(text('TRUNCATE TABLE question_bank CASCADE'))
        await session.commit()
        print('All questions, papers, and assessments have been deleted.')

if __name__ == '__main__':
    asyncio.run(main())

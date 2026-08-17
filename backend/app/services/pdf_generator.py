import os
import io
import zipfile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import inch

from app.db.models.mcq_engine import (
    MCQEGenerationJob,
    MCQEQuestionPaper,
    MCQEQuestionPaperItem,
    MCQETextbook,
    MCQEStudentResult,
    MCQEStudentAnswerDetail,
    MCQEStudentConceptAnalysis,
    MCQEMcq,
)


def register_fonts():
    font_dir = "/app/fonts"
    devanagari_path = os.path.join(font_dir, "NotoSansDevanagari-Regular.ttf")
    gujarati_path = os.path.join(font_dir, "NotoSansGujarati-Regular.ttf")

    if os.path.exists(devanagari_path):
        pdfmetrics.registerFont(TTFont("Devanagari", devanagari_path))
    if os.path.exists(gujarati_path):
        pdfmetrics.registerFont(TTFont("Gujarati", gujarati_path))


async def generate_paper_pdf(db: AsyncSession, paper_id: int) -> bytes:
    register_fonts()

    res = await db.execute(
        select(MCQEQuestionPaper)
        .options(
            selectinload(MCQEQuestionPaper.generation_job),
            selectinload(MCQEQuestionPaper.textbook),
        )
        .where(MCQEQuestionPaper.id == paper_id)
    )
    paper = res.scalar_one_or_none()
    if not paper:
        raise ValueError("Paper not found")

    job = paper.generation_job
    textbook = paper.textbook

    res_items = await db.execute(
        select(MCQEQuestionPaperItem)
        .options(selectinload(MCQEQuestionPaperItem.mcq))
        .where(MCQEQuestionPaperItem.question_paper_id == paper.id)
        .order_by(MCQEQuestionPaperItem.question_number)
    )
    items = res_items.scalars().all()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    font_name = "Helvetica"
    if job.language == "hindi":
        font_name = "Devanagari"
    elif job.language == "gujarati":
        font_name = "Gujarati"

    try:
        c.setFont(font_name, 12)
    except:
        c.setFont("Helvetica", 12)

    # Header
    c.drawString(
        50,
        height - 50,
        f"Class: {job.class_name} | Subject: {job.subject_id} | Book: {textbook.book_name}",
    )
    c.drawString(50, height - 70, f"Paper Code: {paper.paper_code}")
    c.drawString(
        50,
        height - 90,
        "Name: ______________________  Roll No: __________  Date: ________",
    )

    y = height - 130
    c.setFont(font_name, 10)

    for item in items:
        if y < 100:
            c.showPage()
            c.setFont(font_name, 10)
            y = height - 50

        c.drawString(50, y, f"Q{item.question_number}. {item.mcq.question_text}")
        y -= 20
        c.drawString(70, y, f"A) {item.option_a}")
        y -= 15
        c.drawString(70, y, f"B) {item.option_b}")
        y -= 15
        c.drawString(70, y, f"C) {item.option_c}")
        y -= 15
        c.drawString(70, y, f"D) {item.option_d}")
        y -= 30

    c.save()
    return buffer.getvalue()


async def generate_papers_zip(db: AsyncSession, job_id: int) -> bytes:
    res = await db.execute(
        select(MCQEGenerationJob).where(MCQEGenerationJob.id == job_id)
    )
    job = res.scalar_one_or_none()
    if not job:
        raise ValueError("Job not found")

    res_papers = await db.execute(
        select(MCQEQuestionPaper).where(MCQEQuestionPaper.generation_job_id == job.id)
    )
    papers = res_papers.scalars().all()

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for paper in papers:
            pdf_bytes = await generate_paper_pdf(db, paper.id)
            filename = f"{job.class_name}_{job.subject_id}_{job.textbook_id}_{paper.paper_code}.pdf"
            zip_file.writestr(filename, pdf_bytes)

    return zip_buffer.getvalue()


async def generate_marked_answer_sheet(
    db: AsyncSession, student_result_id: int
) -> bytes:
    register_fonts()
    res = await db.execute(
        select(MCQEStudentResult)
        .options(selectinload(MCQEStudentResult.student))
        .where(MCQEStudentResult.id == student_result_id)
    )
    result = res.scalar_one_or_none()
    if not result:
        raise ValueError("Student result not found")

    res_p = await db.execute(
        select(MCQEQuestionPaper)
        .options(selectinload(MCQEQuestionPaper.generation_job))
        .where(MCQEQuestionPaper.paper_code == result.paper_code)
    )
    paper = res_p.scalar_one_or_none()
    if not paper:
        raise ValueError("Paper not found")

    job = paper.generation_job

    res_d = await db.execute(
        select(MCQEStudentAnswerDetail)
        .options(selectinload(MCQEStudentAnswerDetail.mcq))
        .where(MCQEStudentAnswerDetail.student_result_id == result.id)
        .order_by(MCQEStudentAnswerDetail.question_number)
    )
    details = res_d.scalars().all()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    font_name = "Helvetica"
    if job.language == "hindi":
        font_name = "Devanagari"
    elif job.language == "gujarati":
        font_name = "Gujarati"

    try:
        c.setFont(font_name, 12)
    except:
        c.setFont("Helvetica", 12)

    # Header
    c.drawString(
        50,
        height - 50,
        f"Student Roll No: {result.student.roll_number} | Score: {result.score}/40",
    )
    c.drawString(50, height - 70, f"Paper Code: {result.paper_code}")

    y = height - 110
    c.setFont(font_name, 10)

    for d in details:
        if y < 100:
            c.showPage()
            c.setFont(font_name, 10)
            y = height - 50

        mark = "Y" if d.is_correct else f"N (Correct: {d.correct_option})"
        if not d.marked_option:
            mark = "Not Attempted"

        c.drawString(50, y, f"Q{d.question_number}. {d.mcq.question_text}")
        y -= 20
        c.drawString(70, y, f"Selected: {d.marked_option or 'None'} | {mark}")
        y -= 20

    c.save()
    return buffer.getvalue()


async def generate_concept_analysis_report(
    db: AsyncSession, student_result_id: int
) -> bytes:
    register_fonts()
    res = await db.execute(
        select(MCQEStudentResult)
        .options(selectinload(MCQEStudentResult.student))
        .where(MCQEStudentResult.id == student_result_id)
    )
    result = res.scalar_one_or_none()
    if not result:
        raise ValueError("Student result not found")

    res_a = await db.execute(
        select(MCQEStudentConceptAnalysis)
        .options(selectinload(MCQEStudentConceptAnalysis.concept))
        .where(MCQEStudentConceptAnalysis.student_result_id == result.id)
    )
    analysis_records = res_a.scalars().all()

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica", 14)
    c.drawString(50, height - 50, "Concept Understanding Analysis Report")
    c.setFont("Helvetica", 12)
    c.drawString(
        50,
        height - 70,
        f"Roll No: {result.student.roll_number} | Score: {result.score}/40",
    )

    y = height - 110

    strong = []
    weak = []

    c.drawString(50, y, "Concept Breakdown:")
    y -= 20

    for a in analysis_records:
        if y < 100:
            c.showPage()
            y = height - 50

        title = a.concept.concept_title[:40]
        c.drawString(
            50,
            y,
            f"- {title}: {a.questions_correct}/{a.questions_attempted} ({a.classification})",
        )
        y -= 20

        if a.classification == "Strong":
            strong.append(title)
        elif a.classification == "Weak":
            weak.append(title)

    y -= 20
    c.drawString(50, y, "Summary:")
    y -= 20
    c.drawString(50, y, f"Strong in: {', '.join(strong) if strong else 'None'}")
    y -= 20
    c.drawString(50, y, f"Needs improvement in: {', '.join(weak) if weak else 'None'}")

    c.save()
    return buffer.getvalue()

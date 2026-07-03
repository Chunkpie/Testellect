import os
import time
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.models.assessments import School, Assessment, StudentResult

class PDFReportService:
    @staticmethod
    async def generate_school_summary(db: AsyncSession, school_id: int, report_id: int) -> str:
        school = await db.get(School, school_id)
        if not school:
            raise ValueError("School not found")

        os.makedirs(settings.REPORTS_DIR, exist_ok=True)
        filename = f"report_{report_id}_school_{school_id}.pdf"
        filepath = os.path.join(settings.REPORTS_DIR, filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        # Title
        elements.append(Paragraph(f"School Performance Report: {school.name}", styles['Title']))
        elements.append(Spacer(1, 20))

        # Fetch basic data
        stmt = select(Assessment).where(Assessment.school_id == school_id)
        res = await db.execute(stmt)
        assessments = res.scalars().all()
        
        assessment_data = [["Assessment Name", "Date", "Status", "Avg Score"]]
        
        for a in assessments:
            # Get avg score
            sr_stmt = select(StudentResult).where(StudentResult.assessment_id == a.id)
            sr_res = await db.execute(sr_stmt)
            s_results = sr_res.scalars().all()
            
            avg = round(sum(r.percentage for r in s_results if r.percentage) / len(s_results), 2) if s_results else 0
            
            assessment_data.append([
                a.name, 
                str(a.scheduled_date) if a.scheduled_date else "N/A", 
                a.status, 
                f"{avg}%"
            ])

        # Create Table
        t = Table(assessment_data, colWidths=[200, 100, 100, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        elements.append(t)
        
        # Build PDF
        doc.build(elements)
        
        return filepath

    @staticmethod
    async def generate_student_report(db: AsyncSession, student_id: int, report_id: int) -> str:
        # Placeholder for student detailed report
        os.makedirs(settings.REPORTS_DIR, exist_ok=True)
        filename = f"report_{report_id}_student_{student_id}.pdf"
        filepath = os.path.join(settings.REPORTS_DIR, filename)

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"Student Report (ID: {student_id})", styles['Title']))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Detailed analytics go here...", styles['Normal']))
        
        doc.build(elements)
        return filepath

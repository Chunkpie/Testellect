import os
import time
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.models.assessments import Assessment, StudentResult, Student
from app.db.models.auth import School

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
    async def generate_omr_results_report(db: AsyncSession, student_id: int, batch_id: str, evaluated_answers: list, score: float, max_score: float) -> str:
        os.makedirs(settings.REPORTS_DIR, exist_ok=True)
        student = await db.get(Student, student_id)
        student_name = student.full_name if student else "Unknown"
        safe_name = student_name.replace(" ", "_")

        filename = f"omr_results_{safe_name}_{batch_id}.pdf"
        filepath = os.path.join(settings.REPORTS_DIR, filename)
        student_name = student.full_name if student else "Unknown"

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"OMR Results - {student_name} (ID: {student_id})", styles['Title']))
        elements.append(Spacer(1, 10))
        
        percentage = round((score / max_score * 100), 2) if max_score > 0 else 0
        elements.append(Paragraph(f"Score: {score}/{max_score} ({percentage}%)", styles['Heading2']))
        elements.append(Spacer(1, 20))

        table_data = [["Q#", "Your Answer", "Correct Answer", "Result"]]
        for ans in evaluated_answers:
            q_num = ans.get("sequence", ans.get("question_id"))
            student_ans = ans.get("student_answer", "-")
            if not student_ans:
                student_ans = "-"
            correct_ans = ans.get("correct_answer", "-")
            is_correct = "Right" if ans.get("is_correct") else "Wrong"
            
            # Add text color for right/wrong
            if is_correct == "Right":
                result_cell = Paragraph(f"<font color='green'>{is_correct}</font>", styles['Normal'])
            else:
                result_cell = Paragraph(f"<font color='red'>{is_correct}</font>", styles['Normal'])

            table_data.append([str(q_num), student_ans, correct_ans, result_cell])

        t = Table(table_data, colWidths=[50, 100, 100, 100])
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
        doc.build(elements)
        
        return filepath

    @staticmethod
    async def generate_student_report(db: AsyncSession, student_id: int, report_id: int, insights: dict = None) -> str:
        os.makedirs(settings.REPORTS_DIR, exist_ok=True)
        student = await db.get(Student, student_id)
        student_name = student.full_name if student else "Unknown"
        safe_name = student_name.replace(" ", "_")

        filename = f"analytics_report_{safe_name}.pdf"
        filepath = os.path.join(settings.REPORTS_DIR, filename)
        student_name = student.full_name if student else "Unknown"

        doc = SimpleDocTemplate(filepath, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"Student Learning Analysis - {student_name} (ID: {student_id})", styles['Title']))
        elements.append(Spacer(1, 20))
        
        if not insights:
            elements.append(Paragraph("No detailed analytics available yet.", styles['Normal']))
            doc.build(elements)
            return filepath
            
        elements.append(Paragraph("Overall Narrative", styles['Heading2']))
        elements.append(Paragraph(insights.get("narrative", "N/A"), styles['Normal']))
        elements.append(Spacer(1, 15))
        
        elements.append(Paragraph("Strengths", styles['Heading2']))
        for item in insights.get("strengths", []):
            elements.append(Paragraph(f"• {item}", styles['Normal']))
        elements.append(Spacer(1, 15))
        
        elements.append(Paragraph("Areas for Improvement", styles['Heading2']))
        for item in insights.get("areas_for_improvement", []):
            elements.append(Paragraph(f"• {item}", styles['Normal']))
        elements.append(Spacer(1, 15))
        
        elements.append(Paragraph("Recommendations", styles['Heading2']))
        for item in insights.get("recommendations", []):
            elements.append(Paragraph(f"• {item}", styles['Normal']))
            
        doc.build(elements)
        return filepath

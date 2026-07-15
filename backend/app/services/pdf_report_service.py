import os
import time
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.db.models.assessments import Assessment, StudentResult, Student, CompetencyResult
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
    async def generate_student_report(
        db: AsyncSession, 
        student_id: int, 
        report_id: int, 
        insights: dict = None,
        assessment_id: int | None = None
    ) -> str:
        os.makedirs(settings.REPORTS_DIR, exist_ok=True)
        student = await db.get(Student, student_id)
        student_name = student.full_name if student else "Unknown"
        safe_name = student_name.replace(" ", "_")

        filename = f"analytics_report_{safe_name}.pdf"
        filepath = os.path.join(settings.REPORTS_DIR, filename)

        # Setup Document with clean margins
        doc = SimpleDocTemplate(
            filepath,
            pagesize=A4,
            leftMargin=40,
            rightMargin=40,
            topMargin=40,
            bottomMargin=40
        )
        
        # Color System
        c_primary = colors.HexColor("#1e293b")      # Dark Slate
        c_secondary = colors.HexColor("#0f766e")    # Deep Teal
        c_accent = colors.HexColor("#d97706")       # Dark Amber
        c_text = colors.HexColor("#334155")         # Slate 700
        
        styles = getSampleStyleSheet()
        
        # Typography & Styles
        title_style = ParagraphStyle(
            'ReportTitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=c_primary,
            spaceAfter=4
        )
        
        subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=11,
            leading=14,
            textColor=c_secondary,
            spaceAfter=12
        )
        
        h2_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=15,
            textColor=c_primary,
            spaceBefore=12,
            spaceAfter=6,
            keepWithNext=True
        )
        
        body_style = ParagraphStyle(
            'BodyTextCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9.5,
            leading=14,
            textColor=c_text
        )
        
        bullet_style = ParagraphStyle(
            'BulletTextCustom',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=13,
            textColor=c_text,
            leftIndent=12,
            firstLineIndent=-8,
            spaceAfter=4
        )
        
        strength_title_style = ParagraphStyle(
            'StrengthHeader',
            parent=h2_style,
            textColor=colors.HexColor("#15803d"),
            spaceBefore=0,
            spaceAfter=6
        )
        
        improvement_title_style = ParagraphStyle(
            'ImprovementHeader',
            parent=h2_style,
            textColor=colors.HexColor("#b91c1c"),
            spaceBefore=0,
            spaceAfter=6
        )

        elements = []

        # Fetch metadata
        from app.db.models.assessments import Class
        classroom = None
        if student and student.class_id:
            classroom = await db.get(Class, student.class_id)
            
        school = None
        if student and student.school_id:
            school = await db.get(School, student.school_id)
            
        assessment = None
        sr = None
        if assessment_id:
            assessment = await db.get(Assessment, assessment_id)
            sr_stmt = select(StudentResult).where(
                StudentResult.student_id == student_id,
                StudentResult.assessment_id == assessment_id
            )
            sr_res = await db.execute(sr_stmt)
            sr = sr_res.scalar_one_or_none()

        # --- Header Section (Title + Details Box) ---
        details_data = [
            [
                Paragraph("STUDENT:", ParagraphStyle('ML1', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#64748b"))),
                Paragraph(student_name.upper(), ParagraphStyle('MV1', fontName='Helvetica-Bold', fontSize=9, leading=10, textColor=c_primary))
            ],
            [
                Paragraph("CLASS:", ParagraphStyle('ML2', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#64748b"))),
                Paragraph(f"Grade {classroom.grade} - {classroom.section}".upper() if classroom else "N/A", ParagraphStyle('MV2', fontName='Helvetica', fontSize=9, leading=10, textColor=c_primary))
            ],
            [
                Paragraph("SCHOOL:", ParagraphStyle('ML3', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#64748b"))),
                Paragraph(school.name if school else "N/A", ParagraphStyle('MV3', fontName='Helvetica', fontSize=8, leading=9, textColor=c_primary))
            ],
            [
                Paragraph("DATE:", ParagraphStyle('ML4', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#64748b"))),
                Paragraph(time.strftime("%d %b %Y"), ParagraphStyle('MV4', fontName='Helvetica', fontSize=9, leading=10, textColor=c_primary))
            ]
        ]
        
        details_table = Table(details_data, colWidths=[55, 145])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ]))
        
        header_table = Table([
            [
                [
                    Paragraph("STUDENT LEARNING ANALYSIS", subtitle_style),
                    Paragraph(student_name, title_style),
                    Paragraph(f"Assessment: {assessment.name if assessment else 'General performance evaluation'}", ParagraphStyle('AS', fontName='Helvetica', fontSize=9, leading=11, textColor=c_text))
                ],
                details_table
            ]
        ], colWidths=[300, 215])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 15))

        # --- Metrics Dashboard Grid ---
        if sr:
            comp_stmt = select(CompetencyResult).where(CompetencyResult.student_result_id == sr.id)
            comp_res = await db.execute(comp_stmt)
            comp_list = comp_res.scalars().all()
            total_questions = sum(c.questions_attempted or 0 for c in comp_list)
            total_correct = sum(c.questions_correct or 0 for c in comp_list)
            total_incorrect = total_questions - total_correct
            perc_val = sr.percentage or 0.0
            
            metrics_data = [
                [
                    Paragraph("TOTAL QUESTIONS", ParagraphStyle('M1', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#64748b"), alignment=1)),
                    Paragraph("CORRECT ANSWERS", ParagraphStyle('M2', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#16a34a"), alignment=1)),
                    Paragraph("INCORRECT / MISSED", ParagraphStyle('M3', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor("#dc2626"), alignment=1)),
                    Paragraph("OVERALL SCORE", ParagraphStyle('M4', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=c_secondary, alignment=1))
                ],
                [
                    Paragraph(str(total_questions), ParagraphStyle('V1', fontName='Helvetica-Bold', fontSize=18, leading=20, textColor=c_primary, alignment=1)),
                    Paragraph(str(total_correct), ParagraphStyle('V2', fontName='Helvetica-Bold', fontSize=18, leading=20, textColor=colors.HexColor("#16a34a"), alignment=1)),
                    Paragraph(str(total_incorrect), ParagraphStyle('V3', fontName='Helvetica-Bold', fontSize=18, leading=20, textColor=colors.HexColor("#dc2626"), alignment=1)),
                    Paragraph(f"{perc_val:.1f}%", ParagraphStyle('V4', fontName='Helvetica-Bold', fontSize=18, leading=20, textColor=c_secondary, alignment=1))
                ]
            ]
            
            metrics_table = Table(metrics_data, colWidths=[128, 128, 128, 131])
            metrics_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ]))
            elements.append(metrics_table)
            elements.append(Spacer(1, 12))

        # --- Fallback if no insights ---
        if not insights:
            elements.append(Paragraph("No detailed learning analytics available yet for this student.", body_style))
            doc.build(elements)
            return filepath

        # --- Narrative Callout Box ---
        narrative_text = insights.get("narrative", "No narrative evaluation available.")
        
        # Support multi-paragraph narratives by splitting on newlines
        narrative_paras = []
        for p_text in narrative_text.split('\n'):
            p_text = p_text.strip()
            if p_text:
                narrative_paras.append(Paragraph(p_text, body_style))
                narrative_paras.append(Spacer(1, 6)) # add small space between paragraphs
                
        if not narrative_paras:
            narrative_paras = [Paragraph("No narrative evaluation available.", body_style)]
        else:
            # remove the last spacer
            narrative_paras.pop()
        
        narrative_table = Table([[narrative_paras]], colWidths=[515])
        narrative_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f0fdfa")),
            ('LINELEFT', (0, 0), (0, -1), 4, c_secondary),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#ccfbf1")),
        ]))
        
        elements.append(Paragraph("Overall Evaluation Narrative", h2_style))
        elements.append(narrative_table)
        elements.append(Spacer(1, 10))

        # --- Strengths & Areas for Improvement (Side-by-Side Cards) ---
        strengths_paras = [Paragraph("Strengths & Mastered Concepts", strength_title_style)]
        for s in insights.get("strengths", []):
            strengths_paras.append(Paragraph(f"• {s}", bullet_style))
        if len(insights.get("strengths", [])) == 0:
            strengths_paras.append(Paragraph("• No specific strengths identified yet.", bullet_style))
            
        improvement_paras = [Paragraph("Areas for Improvement", improvement_title_style)]
        for imp in insights.get("areas_for_improvement", []):
            improvement_paras.append(Paragraph(f"• {imp}", bullet_style))
        if len(insights.get("areas_for_improvement", [])) == 0:
            improvement_paras.append(Paragraph("• No immediate improvement areas identified.", bullet_style))
            
        side_outer_table = Table([
            [strengths_paras, '', improvement_paras]
        ], colWidths=[250, 15, 250])
        side_outer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            
            # Left Card Styling (Strengths)
            ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#f0fdf4")),
            ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor("#bbf7d0")),
            ('TOPPADDING', (0, 0), (0, 0), 10),
            ('BOTTOMPADDING', (0, 0), (0, 0), 10),
            ('LEFTPADDING', (0, 0), (0, 0), 12),
            ('RIGHTPADDING', (0, 0), (0, 0), 12),
            
            # Right Card Styling (Improvement)
            ('BACKGROUND', (2, 0), (2, 0), colors.HexColor("#fef2f2")),
            ('BOX', (2, 0), (2, 0), 0.5, colors.HexColor("#fecaca")),
            ('TOPPADDING', (2, 0), (2, 0), 10),
            ('BOTTOMPADDING', (2, 0), (2, 0), 10),
            ('LEFTPADDING', (2, 0), (2, 0), 12),
            ('RIGHTPADDING', (2, 0), (2, 0), 12),
        ]))
        
        elements.append(side_outer_table)
        elements.append(Spacer(1, 10))

        # --- Recommendations Card (Action Plan) ---
        rec_paras = []
        for rec in insights.get("recommendations", []):
            rec_paras.append(Paragraph(f"• {rec}", bullet_style))
        if len(insights.get("recommendations", [])) == 0:
            rec_paras.append(Paragraph("• Continue regular practice and review correct concepts.", bullet_style))
            
        rec_table = Table([[rec_paras]], colWidths=[515])
        rec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
            ('LINELEFT', (0, 0), (0, -1), 4, c_accent),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#fef3c7")),
        ]))
        
        elements.append(Paragraph("Targeted Action Plan & Recommendations", h2_style))
        elements.append(rec_table)

        doc.build(elements)
        return filepath

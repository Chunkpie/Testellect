import os
import io
import urllib.request
from datetime import datetime
from typing import List, Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, ListFlowable, ListItem
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.core.config import settings

FONTS_DIR = os.path.join(settings.FILE_STORAGE_PATH, "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

# URLs for Mukta fonts for multi-language support (supports both Latin and Regional)
FONTS_TO_DOWNLOAD = {
    "Mukta-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/mukta/Mukta-Regular.ttf",
    "MuktaVaani-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/muktavaani/MuktaVaani-Regular.ttf"
}

def ensure_fonts():
    for filename, url in FONTS_TO_DOWNLOAD.items():
        filepath = os.path.join(FONTS_DIR, filename)
        if not os.path.exists(filepath):
            try:
                urllib.request.urlretrieve(url, filepath)
            except Exception as e:
                print(f"Warning: Failed to download {filename}: {e}")

class PDFPaperService:
    def __init__(self):
        ensure_fonts()
        self._register_fonts()
        
    def _register_fonts(self):
        try:
            pdfmetrics.registerFont(TTFont('HindiFont', os.path.join(FONTS_DIR, 'Mukta-Regular.ttf')))
            pdfmetrics.registerFont(TTFont('GujaratiFont', os.path.join(FONTS_DIR, 'MuktaVaani-Regular.ttf')))
        except Exception:
            pass # Fallback to default if fonts missing

    def generate_paper_pdf(
        self, 
        paper_info: Dict[str, Any], 
        questions: List[Dict[str, Any]], 
        language: str = "english"
    ) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=36, leftMargin=36,
            topMargin=36, bottomMargin=36
        )
        
        Story = []
        styles = getSampleStyleSheet()
        
        # Determine font based on language
        font_name = 'HindiFont'
        if language.lower() == 'gujarati':
            font_name = 'GujaratiFont'
            
        # Fallback to Helvetica if TTF wasn't loaded
        if font_name not in pdfmetrics.getRegisteredFontNames():
            font_name = 'Helvetica'

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName=font_name,
            alignment=1, # Center
            spaceAfter=16,
            textColor=colors.HexColor('#1e3a8a') # Dark blue
        )
        
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontName=font_name,
            alignment=1,
            spaceAfter=8,
            fontSize=11,
            textColor=colors.HexColor('#4b5563') # Gray
        )
        
        question_style = ParagraphStyle(
            'QuestionStyle',
            parent=styles['Normal'],
            fontName=font_name,
            spaceAfter=12,
            fontSize=11,
            leading=16
        )
        
        option_style = ParagraphStyle(
            'OptionStyle',
            parent=styles['Normal'],
            fontName=font_name,
            leftIndent=20,
            spaceAfter=6,
            fontSize=11
        )

        # Header
        current_date = datetime.now().strftime("%d %B %Y")
        Story.append(Paragraph("<b>GSEB-NAS Model Test Paper</b>", title_style))
        Story.append(Paragraph(f"Paper Variant: {paper_info.get('name', 'N/A')} | Date: {current_date} | Language: {language.title()}", info_style))
        
        # We try to show the actual subject name if available instead of just subject ID
        sub_name = paper_info.get('subject_name', f"ID {paper_info.get('subject_id', 'N/A')}")
        duration = paper_info.get('duration_minutes')
        if not duration:
            duration = 60
        info_text = f"Grade: {paper_info.get('grade', 'N/A')} | Subject: {sub_name} | Total Marks: {paper_info.get('total_marks', 'N/A')} | Duration: {duration} min"
        Story.append(Paragraph(info_text, info_style))
        Story.append(Spacer(1, 24))

        # Questions
        for q in questions:
            # Question Text
            q_num = q['sequence']
            # Based on language, extract the correct text field from the question dict
            q_text = q.get('question_text_en', '')
            if language.lower() == 'hindi':
                q_text = q.get('question_text_hi', q_text)
            elif language.lower() == 'gujarati':
                q_text = q.get('question_text_gu', q_text)
                
            Story.append(Paragraph(f"<b>Q{q_num}.</b> {q_text}", question_style))
            
            # Embed Image if present
            image_path = q.get('image_path')
            if image_path:
                full_path = os.path.join(settings.FILE_STORAGE_PATH, image_path.replace('/storage/', ''))
                if os.path.exists(full_path):
                    Story.append(RLImage(full_path, width=200, height=150, kind='proportional'))
                    Story.append(Spacer(1, 12))

            # Options
            options = q.get('options', [])
            for opt in options:
                opt_text = opt.get('option_text_en', '')
                if language.lower() == 'hindi':
                    opt_text = opt.get('option_text_hi', opt_text)
                elif language.lower() == 'gujarati':
                    opt_text = opt.get('option_text_gu', opt_text)
                    
                Story.append(Paragraph(f"{opt.get('prefix', '•')} {opt_text}", option_style))
            
            Story.append(Spacer(1, 12))

        doc.build(Story)
        buffer.seek(0)
        return buffer

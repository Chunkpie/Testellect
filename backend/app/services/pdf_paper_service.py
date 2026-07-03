import os
import io
import urllib.request
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

# URLs for Noto Sans fonts for multi-language support
FONTS_TO_DOWNLOAD = {
    "NotoSans-Regular.ttf": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf",
    "NotoSansDevanagari-Regular.ttf": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
    "NotoSansGujarati-Regular.ttf": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansGujarati/NotoSansGujarati-Regular.ttf"
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
            pdfmetrics.registerFont(TTFont('NotoSans', os.path.join(FONTS_DIR, 'NotoSans-Regular.ttf')))
            pdfmetrics.registerFont(TTFont('NotoDevanagari', os.path.join(FONTS_DIR, 'NotoSansDevanagari-Regular.ttf')))
            pdfmetrics.registerFont(TTFont('NotoGujarati', os.path.join(FONTS_DIR, 'NotoSansGujarati-Regular.ttf')))
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
        font_name = 'Helvetica'
        if language.lower() == 'hindi':
            font_name = 'NotoDevanagari'
        elif language.lower() == 'gujarati':
            font_name = 'NotoGujarati'
            
        # Fallback to Helvetica if TTF wasn't loaded
        if font_name not in pdfmetrics.getRegisteredFontNames():
            font_name = 'Helvetica'

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName=font_name,
            alignment=1, # Center
            spaceAfter=12
        )
        
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontName=font_name,
            alignment=1,
            spaceAfter=24
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
        Story.append(Paragraph(f"Paper: {paper_info['name']} (Language: {language.title()})", title_style))
        info_text = f"Grade: {paper_info['grade']} | Subject ID: {paper_info['subject_id']} | Total Marks: {paper_info['total_marks']} | Duration: {paper_info['duration_minutes']} min"
        Story.append(Paragraph(info_text, info_style))
        Story.append(Spacer(1, 12))

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

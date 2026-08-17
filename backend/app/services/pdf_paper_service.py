import os
import io
import urllib.request
from datetime import datetime
from typing import List, Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image as RLImage,
    ListFlowable,
    ListItem,
    Table,
    TableStyle,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from app.core.config import settings

FONTS_DIR = os.path.join(settings.FILE_STORAGE_PATH, "fonts")
os.makedirs(FONTS_DIR, exist_ok=True)

# URLs for Mukta fonts for multi-language support (supports both Latin and Regional)
FONTS_TO_DOWNLOAD = {
    "Mukta-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/mukta/Mukta-Regular.ttf",
    "MuktaVaani-Regular.ttf": "https://raw.githubusercontent.com/google/fonts/main/ofl/muktavaani/MuktaVaani-Regular.ttf",
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
            pdfmetrics.registerFont(
                TTFont("HindiFont", os.path.join(FONTS_DIR, "Mukta-Regular.ttf"))
            )
            pdfmetrics.registerFont(
                TTFont(
                    "GujaratiFont", os.path.join(FONTS_DIR, "MuktaVaani-Regular.ttf")
                )
            )
        except Exception:
            pass  # Fallback to default if fonts missing

    def generate_paper_pdf(
        self,
        paper_info: Dict[str, Any],
        questions: List[Dict[str, Any]],
        language: str = "english",
    ) -> io.BytesIO:
        buffer = io.BytesIO()

        # Margins set to 40pt for a cleaner look
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=40,
            leftMargin=40,
            topMargin=45,
            bottomMargin=50,
        )

        Story = []
        styles = getSampleStyleSheet()

        # Determine font based on language
        font_name = "HindiFont"
        if language.lower() == "gujarati":
            font_name = "GujaratiFont"

        # Fallback to Helvetica if TTF wasn't loaded
        if font_name not in pdfmetrics.getRegisteredFontNames():
            font_name = "Helvetica"

        # Modern color palette
        primary_color = colors.HexColor("#0f172a")  # Charcoal Slate
        text_color = colors.HexColor("#334155")  # Dark Grey
        accent_color = colors.HexColor("#2563eb")  # Classic Royal Blue
        border_color = colors.HexColor("#cbd5e1")  # Light slate border

        # Styles definition
        title_style = ParagraphStyle(
            "HeaderTitle",
            fontName=font_name,
            fontSize=16,
            leading=20,
            textColor=primary_color,
            fontStyle="bold",
            spaceAfter=4,
        )

        meta_label_style = ParagraphStyle(
            "MetaLabel",
            fontName=font_name,
            fontSize=10,
            leading=14,
            textColor=text_color,
            alignment=0,  # Left
        )

        meta_right_style = ParagraphStyle(
            "MetaRight",
            fontName=font_name,
            fontSize=10,
            leading=14,
            textColor=text_color,
            alignment=2,  # Right
        )

        question_style = ParagraphStyle(
            "QuestionStyle",
            parent=styles["Normal"],
            fontName=font_name,
            spaceBefore=14,
            spaceAfter=8,
            fontSize=10.5,
            leading=15,
            textColor=primary_color,
        )

        option_style = ParagraphStyle(
            "OptionStyle",
            parent=styles["Normal"],
            fontName=font_name,
            leftIndent=15,
            spaceAfter=5,
            fontSize=10,
            leading=14,
            textColor=text_color,
        )

        # Header structured block
        current_date = datetime.now().strftime("%d %B %Y")
        sub_name = paper_info.get(
            "subject_name", f"ID {paper_info.get('subject_id', 'N/A')}"
        )
        duration = paper_info.get("duration_minutes") or 60

        # Constructing header layout as a clean table
        header_data = [
            [
                Paragraph(f"<b>TESTELLECT EVALUATION PLATFORM</b>", title_style),
                Paragraph(
                    f"<b>Grade:</b> {paper_info.get('grade', 'N/A')}<br/><b>Subject:</b> {sub_name}",
                    meta_right_style,
                ),
            ],
            [
                Paragraph(
                    f"<b>Paper Set:</b> {paper_info.get('name', 'N/A')} | <b>Date:</b> {current_date}",
                    meta_label_style,
                ),
                Paragraph(
                    f"<b>Total Marks:</b> {paper_info.get('total_marks', 'N/A')} M | <b>Duration:</b> {duration} Min",
                    meta_right_style,
                ),
            ],
        ]

        header_table = Table(header_data, colWidths=[315, 200])
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    (
                        "LINEBELOW",
                        (0, 1),
                        (-1, 1),
                        1.5,
                        primary_color,
                    ),  # Bold horizontal rule beneath header
                ]
            )
        )

        Story.append(header_table)
        Story.append(Spacer(1, 15))

        # Questions
        for q in questions:
            # Question Text
            q_num = q["sequence"]
            q_text = q.get("question_text_en", "")
            if language.lower() == "hindi":
                q_text = q.get("question_text_hi", q_text)
            elif language.lower() == "gujarati":
                q_text = q.get("question_text_gu", q_text)

            Story.append(Paragraph(f"<b>Q{q_num}.</b> {q_text}", question_style))

            # Embed Image if present
            image_path = q.get("image_path")
            if image_path:
                full_path = os.path.join(
                    settings.FILE_STORAGE_PATH, image_path.replace("/storage/", "")
                )
                if os.path.exists(full_path):
                    Story.append(
                        RLImage(full_path, width=220, height=140, kind="proportional")
                    )
                    Story.append(Spacer(1, 8))

            # Options formatting (uses 2x2 grid if options are short)
            options = q.get("options", [])
            opt_paragraphs = []
            max_len = 0
            for opt in options:
                opt_text = opt.get("option_text_en", "")
                if language.lower() == "hindi":
                    opt_text = opt.get("option_text_hi", opt_text)
                elif language.lower() == "gujarati":
                    opt_text = opt.get("option_text_gu", opt_text)

                prefix = opt.get("prefix", "•")
                if not prefix.endswith("."):
                    prefix = f"{prefix}."

                full_opt_text = f"<b>{prefix}</b> {opt_text}"
                max_len = max(max_len, len(opt_text))
                opt_paragraphs.append(Paragraph(full_opt_text, option_style))

            if max_len < 35 and len(opt_paragraphs) == 4:
                # 2x2 Grid alignment
                data = [
                    [opt_paragraphs[0], opt_paragraphs[1]],
                    [opt_paragraphs[2], opt_paragraphs[3]],
                ]
                opt_table = Table(data, colWidths=[250, 250])
                opt_table.setStyle(
                    TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 5),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                            ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ]
                    )
                )
                Story.append(opt_table)
            else:
                for opt_p in opt_paragraphs:
                    Story.append(opt_p)

            Story.append(Spacer(1, 6))

        # Canvas decoration callback for running footer
        def draw_decorations(canvas, doc):
            canvas.saveState()
            canvas.setStrokeColor(border_color)
            canvas.setLineWidth(0.5)
            # Bottom divider line
            canvas.line(40, 45, 555, 45)

            # Footer text and page number
            canvas.setFont("Helvetica", 8.5)
            canvas.setFillColor(text_color)
            canvas.drawString(
                40, 30, "Testellect Platform — Confidential Assessment Tool"
            )
            canvas.drawRightString(555, 30, f"Page {doc.page}")
            canvas.restoreState()

        # Build document with decoration callback
        doc.build(Story, onFirstPage=draw_decorations, onLaterPages=draw_decorations)
        buffer.seek(0)
        return buffer

import io
import json
import os
import time

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, HexColor, lightgrey

from app.core.config import settings

OPTIONS = ["A", "B", "C", "D"]
BUBBLE_R = 4.5 * mm
ROW_H = 8.5 * mm
MARGIN = 15 * mm
LABEL_W = 10 * mm
QR_SIZE = 32 * mm


def _draw_qr(c: canvas.Canvas, x: float, y: float, data: str, tmp_dir: str) -> None:
    qr_img = qrcode.make(data, box_size=2, border=1)
    tmp_path = os.path.join(tmp_dir, f"qr_{int(time.time() * 1000)}_{hash(data)}.png")
    qr_img.save(tmp_path)
    c.drawImage(tmp_path, x, y, width=QR_SIZE, height=QR_SIZE)
    # Draw a thin box around it
    c.setLineWidth(0.5)
    c.rect(x, y, QR_SIZE, QR_SIZE)
    try:
        os.remove(tmp_path)
    except OSError:
        pass


def _draw_bubbles(
    c: canvas.Canvas, x: float, y: float, qnum: int, bubble_r: float, label_w: float
) -> None:
    c.saveState()
    # Question Number
    c.setFont("Helvetica-Bold", 9 if bubble_r < 3.5 * mm else 10)
    # Right align the question number slightly
    q_str = f"{qnum:02d}."
    c.drawString(x, y - 3, q_str)

    bx = x + label_w
    for opt in OPTIONS:
        # Draw bubble
        c.setLineWidth(0.8 if bubble_r < 3.5 * mm else 1)
        c.setStrokeColor(black)
        c.circle(bx, y, bubble_r, fill=0)
        # Center the text inside the bubble
        c.setFont("Helvetica", 5.5 if bubble_r < 3.5 * mm else 7)
        c.drawCentredString(bx, y - (2.0 if bubble_r < 3.5 * mm else 2.5), opt)
        bx += 2.5 * bubble_r
    c.restoreState()


def _draw_fiducials(c: canvas.Canvas, w: float, h: float):
    # Draw 4 solid black squares at the corners as fiducials
    c.saveState()
    c.setFillColor(black)
    s = 8 * mm  # size of fiducial
    m = 8 * mm  # margin from page edge
    # Top Left
    c.rect(m, h - m - s, s, s, fill=1)
    # Top Right
    c.rect(w - m - s, h - m - s, s, s, fill=1)
    # Bottom Left
    c.rect(m, m, s, s, fill=1)
    # Bottom Right
    c.rect(w - m - s, m, s, s, fill=1)
    c.restoreState()


def generate_omr_pdf(
    paper_id: int,
    students: list,
    school_id: int,
    paper_name: str | None = None,
    total_questions: int | None = None,
    batch_id: str | None = None,
) -> str:
    if total_questions is None or total_questions < 1:
        total_questions = 30
    if batch_id is None:
        batch_id = f"BATCH_{paper_id}_{int(time.time())}"

    # Determine layout parameters dynamically to fit everything on a single page
    if total_questions <= 30:
        num_cols = 2
        bubble_r = 4.2 * mm
        row_h = 8.5 * mm
        label_w = 10 * mm
    elif total_questions <= 60:
        num_cols = 3
        bubble_r = 3.5 * mm
        row_h = 7.5 * mm
        label_w = 9 * mm
    else:
        num_cols = 4
        bubble_r = 2.8 * mm
        row_h = 6.2 * mm
        label_w = 8 * mm

    os.makedirs(settings.REPORTS_DIR, exist_ok=True)
    ts = int(time.time())
    filename = f"omr_{paper_id}_{ts}.pdf"
    filepath = os.path.join(settings.REPORTS_DIR, filename)

    c = canvas.Canvas(filepath, pagesize=A4)
    W, H = A4

    student_count = len(students)
    for sheet_num, student in enumerate(students, start=1):
        _draw_fiducials(c, W, H)

        # Outer Border for the main content area
        c.setLineWidth(2)
        c.rect(MARGIN, MARGIN, W - 2 * MARGIN, H - 2 * MARGIN)

        # --- Header Section ---
        header_y = H - MARGIN
        c.saveState()
        c.setFillColor(HexColor("#F8F9FA"))
        c.rect(MARGIN, header_y - 25 * mm, W - 2 * MARGIN, 25 * mm, fill=1, stroke=0)
        c.restoreState()

        # Separator line under header
        c.setLineWidth(1)
        c.line(MARGIN, header_y - 25 * mm, W - MARGIN, header_y - 25 * mm)

        # Title
        c.setFont("Helvetica-Bold", 18)
        c.drawString(MARGIN + 5 * mm, header_y - 10 * mm, "TESTELLECT")
        c.setFont("Helvetica", 14)
        c.drawString(MARGIN + 5 * mm, header_y - 17 * mm, "OMR Answer Sheet")

        # Info
        c.setFont("Helvetica", 9)
        if paper_name:
            c.drawString(
                MARGIN + 5 * mm, header_y - 22 * mm, f"Exam: {paper_name.upper()}"
            )

        # Right side of header (Sheet X of Y)
        c.drawRightString(
            W - MARGIN - 5 * mm,
            header_y - 10 * mm,
            f"Sheet {sheet_num} of {student_count}",
        )

        # --- QR Code ---
        qr_y = header_y - 25 * mm - 5 * mm - QR_SIZE
        qr_x = W - MARGIN - 5 * mm - QR_SIZE
        qr_payload = json.dumps(
            {
                "batch_id": batch_id,
                "paper_id": paper_id,
                "school_id": school_id,
                "student_id": student.id,
            }
        )
        _draw_qr(c, qr_x, qr_y, qr_payload, settings.REPORTS_DIR)

        # --- Student Info Section (Left of QR) ---
        info_y = header_y - 25 * mm - 5 * mm
        info_w = W - 2 * MARGIN - QR_SIZE - 15 * mm

        c.saveState()
        c.setLineWidth(0.5)
        c.rect(MARGIN + 5 * mm, info_y - QR_SIZE, info_w, QR_SIZE)

        # Title of Info Box
        c.setFillColor(lightgrey)
        c.rect(MARGIN + 5 * mm, info_y - 6 * mm, info_w, 6 * mm, fill=1, stroke=1)
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGIN + 7 * mm, info_y - 4.5 * mm, "STUDENT DETAILS")

        c.setFont("Helvetica-Bold", 11)
        c.drawString(
            MARGIN + 7 * mm, info_y - 15 * mm, f"Name:  {student.full_name.upper()}"
        )
        c.drawString(
            MARGIN + 7 * mm,
            info_y - 25 * mm,
            f"Roll No: {student.roll_number or 'N/A'}",
        )
        c.restoreState()

        # --- Instructions ---
        inst_y = info_y - QR_SIZE - 10 * mm
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(
            MARGIN + 5 * mm,
            inst_y,
            "Instructions: Darken the circles completely using a dark pen/pencil. Do not fold or scratch the sheet.",
        )

        # --- Questions Section ---
        c.setLineWidth(1)
        c.line(MARGIN, inst_y - 5 * mm, W - MARGIN, inst_y - 5 * mm)

        content_w = W - 2 * MARGIN
        section_w = content_w / num_cols
        col_w_content = label_w + 8.5 * bubble_r

        # Draw vertical dividers
        c.setLineWidth(0.5)
        c.setStrokeColor(lightgrey)
        for col in range(1, num_cols):
            div_x = MARGIN + col * section_w
            c.line(div_x, inst_y - 5 * mm, div_x, MARGIN)

        q_per_col = (total_questions + num_cols - 1) // num_cols

        for col in range(num_cols):
            col_x = MARGIN + col * section_w + (section_w - col_w_content) / 2
            start_q = col * q_per_col + 1
            end_q = min(start_q + q_per_col - 1, total_questions)
            q_y = inst_y - 10 * mm

            for qnum in range(start_q, end_q + 1):
                _draw_bubbles(c, col_x, q_y, qnum, bubble_r, label_w)
                q_y -= row_h

        c.showPage()

    c.save()
    return filepath

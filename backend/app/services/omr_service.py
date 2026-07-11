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


def _draw_bubbles(c: canvas.Canvas, x: float, y: float, qnum: int) -> None:
    c.saveState()
    # Question Number
    c.setFont("Helvetica-Bold", 10)
    # Right align the question number slightly
    q_str = f"{qnum:02d}."
    c.drawString(x, y - 3, q_str)
    
    bx = x + LABEL_W
    for opt in OPTIONS:
        # Draw bubble
        c.setLineWidth(1)
        c.setStrokeColor(black)
        c.circle(bx, y, BUBBLE_R, fill=0)
        # Center the text inside the bubble
        c.setFont("Helvetica", 7)
        c.drawCentredString(bx, y - 2.5, opt)
        bx += 2.5 * BUBBLE_R
    c.restoreState()


def _draw_fiducials(c: canvas.Canvas, w: float, h: float):
    # Draw 4 solid black squares at the corners as fiducials
    c.saveState()
    c.setFillColor(black)
    s = 8 * mm # size of fiducial
    m = 8 * mm # margin from page edge
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
        c.rect(MARGIN, header_y - 25*mm, W - 2*MARGIN, 25*mm, fill=1, stroke=0)
        c.restoreState()

        # Separator line under header
        c.setLineWidth(1)
        c.line(MARGIN, header_y - 25*mm, W - MARGIN, header_y - 25*mm)

        # Title
        c.setFont("Helvetica-Bold", 18)
        c.drawString(MARGIN + 5*mm, header_y - 10*mm, "TESTELLECT")
        c.setFont("Helvetica", 14)
        c.drawString(MARGIN + 5*mm, header_y - 17*mm, "OMR Answer Sheet")
        
        # Info
        c.setFont("Helvetica", 9)
        if paper_name:
            c.drawString(MARGIN + 5*mm, header_y - 22*mm, f"Exam: {paper_name.upper()}")
        
        # Right side of header (Sheet X of Y)
        c.drawRightString(W - MARGIN - 5*mm, header_y - 10*mm, f"Sheet {sheet_num} of {student_count}")

        # --- QR Code ---
        # Placed below the header, right aligned
        qr_y = header_y - 25*mm - 5*mm - QR_SIZE
        qr_x = W - MARGIN - 5*mm - QR_SIZE
        qr_payload = json.dumps({
            "batch_id": batch_id, 
            "paper_id": paper_id, 
            "school_id": school_id,
            "student_id": student.id
        })
        _draw_qr(c, qr_x, qr_y, qr_payload, settings.REPORTS_DIR)

        # --- Student Info Section (Left of QR) ---
        info_y = header_y - 25*mm - 5*mm
        info_w = W - 2*MARGIN - QR_SIZE - 15*mm
        
        c.saveState()
        c.setLineWidth(0.5)
        c.rect(MARGIN + 5*mm, info_y - QR_SIZE, info_w, QR_SIZE)
        
        # Title of Info Box
        c.setFillColor(lightgrey)
        c.rect(MARGIN + 5*mm, info_y - 6*mm, info_w, 6*mm, fill=1, stroke=1)
        c.setFillColor(black)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(MARGIN + 7*mm, info_y - 4.5*mm, "STUDENT DETAILS")
        
        c.setFont("Helvetica-Bold", 11)
        c.drawString(MARGIN + 7*mm, info_y - 15*mm, f"Name:  {student.full_name.upper()}")
        c.drawString(MARGIN + 7*mm, info_y - 25*mm, f"Roll No: {student.roll_number or 'N/A'}")
        c.restoreState()

        # --- Instructions ---
        inst_y = info_y - QR_SIZE - 10*mm
        c.setFont("Helvetica-Oblique", 9)
        c.drawString(MARGIN + 5*mm, inst_y, "Instructions: Darken the circles completely using a dark pen/pencil. Do not fold or scratch the sheet.")

        # --- Questions Section ---
        # Draw a line above questions
        c.setLineWidth(1)
        c.line(MARGIN, inst_y - 5*mm, W - MARGIN, inst_y - 5*mm)

        q_per_col = (total_questions + 1) // 2
        col_w = (W - 2 * MARGIN) / 2
        
        # Draw a vertical divider between columns
        c.setLineWidth(0.5)
        c.setStrokeColor(lightgrey)
        c.line(MARGIN + col_w, inst_y - 5*mm, MARGIN + col_w, MARGIN)

        for col in range(2):
            # Center the column content within its half
            col_x = MARGIN + col * col_w + (col_w - (LABEL_W + 4 * 2.5 * BUBBLE_R)) / 2
            start_q = col * q_per_col + 1
            end_q = min(start_q + q_per_col - 1, total_questions)
            q_y = inst_y - 15 * mm

            for qnum in range(start_q, end_q + 1):
                if q_y < MARGIN + 15 * mm:
                    c.showPage()
                    _draw_fiducials(c, W, H)
                    c.setLineWidth(2)
                    c.rect(MARGIN, MARGIN, W - 2 * MARGIN, H - 2 * MARGIN)
                    
                    if sheet_num > 1:
                        c.setFont("Helvetica", 8)
                        c.drawString(MARGIN + 5*mm, H - MARGIN - 10*mm, f"Sheet {sheet_num} (cont.) - {student.full_name}")
                    
                    # Restart column positions for new page
                    q_y = H - MARGIN - 25 * mm
                    c.line(MARGIN + col_w, H - MARGIN, MARGIN + col_w, MARGIN) # Redraw center line

                _draw_bubbles(c, col_x, q_y, qnum)
                q_y -= ROW_H

        c.showPage()

    c.save()
    return filepath

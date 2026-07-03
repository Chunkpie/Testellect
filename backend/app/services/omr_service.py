import io
import json
import os
import time

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.core.config import settings

OPTIONS = ["A", "B", "C", "D"]
BUBBLE_R = 6
ROW_H = 7 * mm
MARGIN = 20 * mm
LABEL_W = 8 * mm
QR_SIZE = 36 * mm


def _draw_qr(c: canvas.Canvas, x: float, y: float, data: str, tmp_dir: str) -> None:
    qr_img = qrcode.make(data, box_size=2, border=1)
    tmp_path = os.path.join(tmp_dir, f"qr_{int(time.time() * 1000)}_{hash(data)}.png")
    qr_img.save(tmp_path)
    c.drawImage(tmp_path, x, y, width=QR_SIZE, height=QR_SIZE)
    try:
        os.remove(tmp_path)
    except OSError:
        pass


def _draw_bubbles(c: canvas.Canvas, x: float, y: float, qnum: int) -> None:
    c.saveState()
    c.setFont("Helvetica", 8)
    c.drawString(x, y - 2, f"{qnum}.")
    bx = x + LABEL_W
    for opt in OPTIONS:
        c.circle(bx, y, BUBBLE_R, fill=0)
        c.setFont("Helvetica", 6)
        c.drawString(bx - 1.5, y - BUBBLE_R - 2, opt)
        bx += 2 * (BUBBLE_R + 2)
    c.restoreState()


def generate_omr_pdf(
    paper_id: int,
    student_count: int,
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

    qr_payload = json.dumps({"batch_id": batch_id, "paper_id": paper_id, "school_id": school_id})
    os.makedirs(settings.REPORTS_DIR, exist_ok=True)

    for sheet_num in range(1, student_count + 1):
        # --- QR code ---
        qr_x = W - MARGIN - QR_SIZE
        qr_y = H - MARGIN - QR_SIZE
        _draw_qr(c, qr_x, qr_y, qr_payload, settings.REPORTS_DIR)

        # --- Header ---
        c.setFont("Helvetica-Bold", 14)
        c.drawString(MARGIN, H - MARGIN, "GSEB PARAKH - OMR Answer Sheet")
        c.setFont("Helvetica", 9)
        c.drawString(MARGIN, H - MARGIN - 6 * mm, f"Sheet {sheet_num} of {student_count}")
        if paper_name:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(MARGIN, H - MARGIN - 10 * mm, paper_name)

        # --- Student info fields ---
        info_y = H - MARGIN - 16 * mm
        c.setFont("Helvetica", 9)
        for label in ["Student Name:", "Class:", "Roll Number:"]:
            c.drawString(MARGIN, info_y, label)
            c.line(MARGIN + 28 * mm, info_y - 1, MARGIN + 80 * mm, info_y - 1)
            info_y -= 6 * mm

        # --- Instructions ---
        inst_y = info_y - 3 * mm
        c.setFont("Helvetica", 7)
        c.drawString(MARGIN, inst_y, "Instructions: Fill the circle completely. Do not scratch or overwrite.")

        # --- Questions in two columns ---
        q_per_col = (total_questions + 1) // 2
        col_w = (W - 2 * MARGIN) / 2 - 4 * mm

        for col in range(2):
            col_x = MARGIN + col * (col_w + 8 * mm)
            start_q = col * q_per_col + 1
            end_q = min(start_q + q_per_col - 1, total_questions)
            q_y = inst_y - 8 * mm

            for qnum in range(start_q, end_q + 1):
                if q_y < MARGIN + 15 * mm:
                    c.showPage()
                    if sheet_num > 1:
                        c.setFont("Helvetica", 8)
                        c.drawString(MARGIN, H - MARGIN, f"Sheet {sheet_num} (cont.)")
                    q_y = H - MARGIN - 20 * mm
                _draw_bubbles(c, col_x, q_y, qnum)
                q_y -= ROW_H

        c.showPage()

    c.save()
    return filepath

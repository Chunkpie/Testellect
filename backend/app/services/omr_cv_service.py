import cv2
import numpy as np
import os
import json
import zipfile
import shutil
import tempfile
from typing import Dict, Any, List
from pdf2image import convert_from_path
from pyzbar.pyzbar import decode

class OMRCVService:
    @staticmethod
    def read_qr(image: np.ndarray) -> str:
        """Extract QR code payload from image."""
        decoded = decode(image)
        if decoded:
            return decoded[0].data.decode('utf-8')
        return ""

    @staticmethod
    def order_points(pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    @staticmethod
    def four_point_transform(image, pts):
        rect = OMRCVService.order_points(pts)
        (tl, tr, br, bl) = rect
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        return warped

    @staticmethod
    async def process_image(image_path: str, total_questions: int = 30) -> Dict[str, Any]:
        """
        Process a single scanned OMR image/PDF page.
        Returns extracted answers and metadata.
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")

        # 1. Read QR Code for batch metadata
        qr_payload = OMRCVService.read_qr(image)
        metadata = {}
        if qr_payload:
            try:
                metadata = json.loads(qr_payload)
            except json.JSONDecodeError:
                metadata = {"raw": qr_payload}

        # 2. Preprocess for bubble detection
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 75, 200)

        # Basic document contour finding
        cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        docCnt = None
        if len(cnts) > 0:
            cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
            for c in cnts:
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                if len(approx) == 4:
                    docCnt = approx
                    break

        if docCnt is not None:
            paper = OMRCVService.four_point_transform(gray, docCnt.reshape(4, 2))
        else:
            paper = gray

        thresh = cv2.threshold(paper, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        
        # 3. Find bubbles
        cnts, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        questionCnts = []

        for c in cnts:
            (x, y, w, h) = cv2.boundingRect(c)
            ar = w / float(h)
            # Filter contours that are roughly circular and of expected size
            if w >= 20 and h >= 20 and ar >= 0.9 and ar <= 1.1:
                questionCnts.append(c)
        
        # Sort top-to-bottom
        def sort_contours(cnts, method="top-to-bottom"):
            reverse = False
            i = 1 if method == "top-to-bottom" or method == "bottom-to-top" else 0
            if method == "right-to-left" or method == "bottom-to-top":
                reverse = True
            boundingBoxes = [cv2.boundingRect(c) for c in cnts]
            (cnts, boundingBoxes) = zip(*sorted(zip(cnts, boundingBoxes),
                                                key=lambda b: b[1][i], reverse=reverse))
            return (cnts, boundingBoxes)

        if not questionCnts:
            return {"metadata": metadata, "answers": []}

        questionCnts, _ = sort_contours(questionCnts, method="top-to-bottom")
        
        # Group by rows (y-coordinate proximity)
        rows = []
        current_row = [questionCnts[0]]
        for c in questionCnts[1:]:
            _, y1, _, _ = cv2.boundingRect(current_row[0])
            _, y2, _, _ = cv2.boundingRect(c)
            if abs(y1 - y2) < 20:
                current_row.append(c)
            else:
                rows.append(current_row)
                current_row = [c]
        rows.append(current_row)

        answers = []
        # Sort each row left-to-right
        for i, row in enumerate(rows):
            if len(row) != 4:  # We expect 4 options (A,B,C,D)
                continue
            row, _ = sort_contours(row, method="left-to-right")
            
            bubbled = None
            max_filled = 0
            for j, c in enumerate(row):
                mask = np.zeros(thresh.shape, dtype="uint8")
                cv2.drawContours(mask, [c], -1, 255, -1)
                mask = cv2.bitwise_and(thresh, thresh, mask=mask)
                total = cv2.countNonZero(mask)
                
                if total > max_filled:
                    max_filled = total
                    bubbled = j

            # Simple threshold to ensure it's actually filled
            if max_filled > 300: 
                answer = chr(65 + bubbled) # 0->A, 1->B, etc.
            else:
                answer = ""
            
            answers.append({
                "question_id": i + 1,
                "answer": answer
            })

        return {
            "metadata": metadata,
            "answers": answers
        }

    @staticmethod
    async def process_pdf(pdf_path: str, total_questions: int = 30) -> List[Dict[str, Any]]:
        results = []
        with tempfile.TemporaryDirectory() as path:
            images = convert_from_path(pdf_path, output_folder=path)
            for i, img in enumerate(images):
                img_path = os.path.join(path, f"page_{i}.jpg")
                img.save(img_path, 'JPEG')
                result = await OMRCVService.process_image(img_path, total_questions)
                results.append(result)
        return results

    @staticmethod
    async def process_zip(zip_path: str, total_questions: int = 30) -> List[Dict[str, Any]]:
        results = []
        with tempfile.TemporaryDirectory() as extract_dir:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            for root, _, files in os.walk(extract_dir):
                for file in files:
                    ext = file.lower().split('.')[-1]
                    file_path = os.path.join(root, file)
                    if ext in ['jpg', 'jpeg', 'png']:
                        result = await OMRCVService.process_image(file_path, total_questions)
                        results.append(result)
                    elif ext == 'pdf':
                        pdf_results = await OMRCVService.process_pdf(file_path, total_questions)
                        results.extend(pdf_results)
        return results

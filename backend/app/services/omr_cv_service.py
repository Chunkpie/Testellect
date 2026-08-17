import cv2
import numpy as np
import os
import json
import zipfile
import shutil
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from pdf2image import convert_from_path
from pyzbar.pyzbar import decode
import httpx
import base64
from app.core.config import settings


class OMRCVService:
    # ---- Tunable constants (kept in one place instead of scattered magic numbers) ----
    MIN_PAGE_CONTOUR_AREA_RATIO = 0.65  # a "page" contour must cover >=65% of the frame
    OPTIONS_PER_QUESTION = 4  # A/B/C/D
    FALLBACK_COVERAGE_THRESHOLD = (
        0.8  # trigger Gemini fallback if <80% of questions were read
    )
    FALLBACK_CONFIDENCE_THRESHOLD = (
        0.55  # or if average fill-confidence is too low/ambiguous
    )

    @staticmethod
    def read_qr(image: np.ndarray) -> str:
        """Extract QR code payload from image."""
        decoded = decode(image)
        if decoded:
            return decoded[0].data.decode("utf-8")
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
        tl, tr, br, bl = rect
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        dst = np.array(
            [
                [0, 0],
                [maxWidth - 1, 0],
                [maxWidth - 1, maxHeight - 1],
                [0, maxHeight - 1],
            ],
            dtype="float32",
        )
        M = cv2.getPerspectiveTransform(rect, dst)
        warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
        return warped

    @staticmethod
    def _find_page(gray: np.ndarray) -> np.ndarray:
        """
        Try to find and align the page. Unlike the previous implementation, this
        REFUSES to warp to a contour unless it plausibly covers most of the frame.
        Previously, the largest 4-corner contour found was often an internal box
        (e.g. a "Marks / Roll No" box) rather than the page, which silently
        warped the whole image to a tiny, wrong region.
        """
        img_area = gray.shape[0] * gray.shape[1]
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 75, 200)
        # dilate to help close small gaps in the page border
        edged = cv2.dilate(edged, np.ones((3, 3), np.uint8), iterations=1)

        cnts, _ = cv2.findContours(
            edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if not cnts:
            return gray

        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
        for c in cnts[:15]:
            area = cv2.contourArea(c)
            if area < img_area * OMRCVService.MIN_PAGE_CONTOUR_AREA_RATIO:
                # contours are sorted by area descending, so once we drop below
                # the threshold none of the rest will qualify either
                break
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                return OMRCVService.four_point_transform(gray, approx.reshape(4, 2))

        # No trustworthy page contour found - use the image as-is rather than
        # risking a warp to the wrong region.
        return gray

    @staticmethod
    def _estimate_bubble_size(thresh: np.ndarray) -> Tuple[float, float]:
        """
        Auto-calibrate the expected bubble size directly from this image, rather
        than guessing a fixed fraction of image diagonal (which only holds for one
        specific scan DPI and breaks on any other resolution/crop). We take a wide,
        permissive first pass over all contours, keep the roughly-circular ones,
        and use their MEDIAN size as the calibrated bubble size for the real pass.
        """
        img_diag = (thresh.shape[0] ** 2 + thresh.shape[1] ** 2) ** 0.5
        # generous net: anywhere from tiny noise to a large chunk of the page
        lo, hi = img_diag * 0.001, img_diag * 0.08

        cnts, _ = cv2.findContours(
            thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        sizes = []
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if not (lo <= w <= hi and lo <= h <= hi):
                continue
            ar = w / float(h) if h else 0
            if not (0.6 <= ar <= 1.4):
                continue
            area = cv2.contourArea(c)
            peri = cv2.arcLength(c, True)
            if peri == 0:
                continue
            if 4 * np.pi * area / (peri * peri) < 0.35:
                continue
            sizes.append((w + h) / 2.0)

        if not sizes:
            # fall back to the old diagonal-fraction guess if calibration fails
            return img_diag * 0.006, img_diag * 0.02

        median_size = float(np.median(sizes))
        return median_size * 0.55, median_size * 1.6

    @staticmethod
    def _sort_contours(cnts, method="top-to-bottom"):
        reverse = False
        i = 1 if method in ("top-to-bottom", "bottom-to-top") else 0
        if method in ("right-to-left", "bottom-to-top"):
            reverse = True
        boundingBoxes = [cv2.boundingRect(c) for c in cnts]
        cnts, boundingBoxes = zip(
            *sorted(zip(cnts, boundingBoxes), key=lambda b: b[1][i], reverse=reverse)
        )
        return cnts, boundingBoxes

    @staticmethod
    def _detect_bubble_contours(thresh: np.ndarray) -> List[Any]:
        cnts, _ = cv2.findContours(
            thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        min_dim, max_dim = OMRCVService._estimate_bubble_size(thresh)

        candidates = []
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if not (min_dim <= w <= max_dim and min_dim <= h <= max_dim):
                continue
            ar = w / float(h)
            if not (0.65 <= ar <= 1.35):
                continue
            area = cv2.contourArea(c)
            peri = cv2.arcLength(c, True)
            if peri == 0:
                continue
            circularity = 4 * np.pi * area / (peri * peri)
            if circularity < 0.4:
                continue
            candidates.append(c)
        return candidates

    @staticmethod
    def _group_into_rows_and_chunks(questionCnts: List[Any]) -> List[List[Any]]:
        """Group bubble contours into rows, then into chunks-of-N (questions) within
        each row, then order chunks column-by-column. Row/column tolerances now scale
        with the median detected bubble size instead of fixed pixel constants."""
        if not questionCnts:
            return []

        boxes = [cv2.boundingRect(c) for c in questionCnts]
        median_h = float(np.median([h for (_, _, _, h) in boxes]))
        row_tol = max(median_h * 0.7, 8)

        questionCnts, _ = OMRCVService._sort_contours(
            questionCnts, method="top-to-bottom"
        )

        y_bands = []
        current_band = [questionCnts[0]]
        for c in questionCnts[1:]:
            _, y1, _, _ = cv2.boundingRect(current_band[0])
            _, y2, _, _ = cv2.boundingRect(c)
            if abs(y1 - y2) < row_tol:
                current_band.append(c)
            else:
                y_bands.append(current_band)
                current_band = [c]
        y_bands.append(current_band)

        n = OMRCVService.OPTIONS_PER_QUESTION
        all_chunks = []
        for band in y_bands:
            band, _ = OMRCVService._sort_contours(band, method="left-to-right")
            # Instead of guessing a fixed gap-to-width ratio to decide "same question
            # vs next question" (which only works for one specific layout's spacing),
            # split this row into groups of exactly `n` using the LARGEST gaps as
            # boundaries. This makes no assumption about how far apart options are
            # printed - it just needs option-to-option spacing within a question to be
            # smaller than question-to-question spacing, which is universally true.
            if len(band) < n:
                all_chunks.append(list(band))
                continue

            num_groups = round(len(band) / n)
            if num_groups < 1:
                num_groups = 1

            if num_groups == 1 or len(band) == n:
                all_chunks.append(list(band))
                continue

            gaps = []
            for i in range(1, len(band)):
                x_prev, _, w_prev, _ = cv2.boundingRect(band[i - 1])
                x_cur, _, _, _ = cv2.boundingRect(band[i])
                gaps.append((x_cur - (x_prev + w_prev), i))

            split_points = sorted(
                sorted(gaps, key=lambda g: g[0], reverse=True)[: num_groups - 1],
                key=lambda g: g[1],
            )
            split_indices = [sp[1] for sp in split_points]

            start = 0
            for idx in split_indices:
                all_chunks.append(list(band[start:idx]))
                start = idx
            all_chunks.append(list(band[start:]))

        valid_chunks = [
            chk for chk in all_chunks if len(chk) == OMRCVService.OPTIONS_PER_QUESTION
        ]

        chunk_data = []
        for chk in valid_chunks:
            avg_x = sum(cv2.boundingRect(c)[0] for c in chk) / len(chk)
            avg_y = sum(cv2.boundingRect(c)[1] for c in chk) / len(chk)
            chunk_data.append({"chunk": chk, "avg_x": avg_x, "avg_y": avg_y})
        chunk_data.sort(key=lambda d: d["avg_x"])

        columns = []
        if chunk_data:
            # Split into visual columns (e.g. a left block of questions 1-25 and a
            # right block of 26-50) using relative gap size rather than a fixed
            # pixel threshold, so this adapts to whatever column spacing this
            # particular sheet uses.
            x_gaps = [
                chunk_data[i]["avg_x"] - chunk_data[i - 1]["avg_x"]
                for i in range(1, len(chunk_data))
            ]
            gap_cutoff = (float(np.median(x_gaps)) * 3.0) if x_gaps else 0

            current_col = [chunk_data[0]]
            for i, d in enumerate(chunk_data[1:], start=1):
                if x_gaps[i - 1] > max(gap_cutoff, 1):
                    columns.append(current_col)
                    current_col = [d]
                else:
                    current_col.append(d)
            columns.append(current_col)

        final_sorted_chunks = []
        for col in columns:
            col.sort(key=lambda d: d["avg_y"])
            for d in col:
                final_sorted_chunks.append(d["chunk"])

        return final_sorted_chunks

    @staticmethod
    def _evaluate_fill(row: List[Any], gray: np.ndarray) -> Tuple[Optional[int], float]:
        """
        Decide which bubble (if any) in a question row is filled in.
        Instead of an absolute "count dark pixels > 50" threshold (which breaks
        across resolutions and ink/print colors), this compares the RELATIVE
        darkness of each option against the others in the same row. The option
        that is meaningfully darker than its siblings is the answer; if nothing
        stands out clearly, the question is left blank rather than guessed.
        Returns (index_of_bubbled_option_or_None, confidence 0-1).
        """
        row, _ = OMRCVService._sort_contours(row, method="left-to-right")
        intensities = []
        for c in row:
            x, y, w, h = cv2.boundingRect(c)
            cx, cy = x + w // 2, y + h // 2
            r = max(int(min(w, h) * 0.35), 3)
            mask = np.zeros(gray.shape, dtype="uint8")
            cv2.circle(mask, (cx, cy), r, 255, -1)
            mean_val = cv2.mean(gray, mask=mask)[0]
            intensities.append(mean_val)

        darkest_idx = int(np.argmin(intensities))
        darkest = intensities[darkest_idx]
        others = [v for i, v in enumerate(intensities) if i != darkest_idx]
        others_avg = float(np.mean(others)) if others else darkest

        # relative contrast between the darkest option and the rest
        spread = others_avg - darkest
        # normalize against the paper's dynamic range in this row so the same
        # relative rule works whether the photo is bright or dim
        row_range = max(max(intensities) - min(intensities), 1.0)
        confidence = max(0.0, min(1.0, spread / row_range))

        if confidence < 0.35:
            return None, confidence
        return darkest_idx, confidence

    @staticmethod
    async def process_image(
        image_path: str, total_questions: int = 30, skip_qr: bool = False
    ) -> Dict[str, Any]:
        """
        Process a single scanned OMR image/PDF page.
        Returns extracted answers and metadata, plus a confidence score.
        """
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")

        metadata = {}
        if not skip_qr:
            qr_payload = OMRCVService.read_qr(image)
            if qr_payload:
                try:
                    metadata = json.loads(qr_payload)
                except json.JSONDecodeError:
                    metadata = {"raw": qr_payload}

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = OMRCVService._find_page(
            gray
        )  # only warps if a trustworthy page contour is found

        thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
        questionCnts = OMRCVService._detect_bubble_contours(thresh)
        final_sorted_chunks = OMRCVService._group_into_rows_and_chunks(questionCnts)

        answers = []
        confidences = []
        for i, row in enumerate(final_sorted_chunks):
            bubbled, confidence = OMRCVService._evaluate_fill(row, gray)
            answer = chr(65 + bubbled) if bubbled is not None else ""
            answers.append({"question_id": i + 1, "answer": answer})
            confidences.append(confidence)

        coverage = len(answers) / float(total_questions) if total_questions else 0
        avg_confidence = float(np.mean(confidences)) if confidences else 0.0

        needs_fallback = (
            coverage < OMRCVService.FALLBACK_COVERAGE_THRESHOLD
            or avg_confidence < OMRCVService.FALLBACK_CONFIDENCE_THRESHOLD
        )

        used_fallback = False
        if needs_fallback:
            try:
                gemini_answers = await OMRCVService._vlm_fallback(
                    image_path, total_questions
                )
                if gemini_answers:
                    answers = gemini_answers
                    used_fallback = True
            except Exception:
                import traceback

                traceback.print_exc()
                # keep whatever the CV heuristic found rather than returning nothing

        scan_confidence = 100.0 if used_fallback else round(avg_confidence * 100, 1)

        return {
            "metadata": metadata,
            "answers": answers,
            "scan_confidence": scan_confidence,
            "used_fallback": used_fallback,
            "cv_coverage": round(coverage, 2),
        }

    @staticmethod
    async def _vlm_fallback(
        image_path: str, total_questions: int
    ) -> List[Dict[str, Any]]:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        base64_image = base64.b64encode(image_bytes).decode("utf-8")

        prompt = (
            f"Extract all the answers marked by the student on this OMR sheet. "
            f"There are {total_questions} questions (Q1 to Q{total_questions}). "
            f"IMPORTANT: Students might indicate their answer by fully filling the bubble, OR by using a checkmark (✓), a tick, or a cross (x) over the option. "
            f"Please look very carefully at each option (A, B, C, D) for ANY pen/pencil marks. "
            f"Return a JSON array where each object has 'question_id' (integer), "
            f"'reasoning' (string: describe what marks you see on options A, B, C, D to justify your choice), and "
            f"'answer' (string A, B, C, or D). If a question has absolutely no marks, return an "
            f"empty string for 'answer'. Only return the JSON array, nothing else. Do not wrap in markdown tags."
        )

        # Try Local Ollama Vision Model first
        ollama_url = getattr(settings, "OLLAMA_BASE_URL", "http://ollama:11434")
        ollama_model = getattr(settings, "OLLAMA_VISION_MODEL", "llama3.2-vision")

        if ollama_url and ollama_model:
            try:
                payload = {
                    "model": ollama_model,
                    "prompt": prompt,
                    "images": [base64_image],
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1},
                }
                async with httpx.AsyncClient(timeout=120) as client:
                    response = await client.post(
                        f"{ollama_url}/api/generate", json=payload
                    )
                    if response.status_code == 200:
                        text_resp = response.json().get("response", "[]").strip()
                        # Strip markdown if present
                        if text_resp.startswith("```json"):
                            text_resp = text_resp[7:]
                        elif text_resp.startswith("```"):
                            text_resp = text_resp[3:]
                        if text_resp.endswith("```"):
                            text_resp = text_resp[:-3]
                        text_resp = text_resp.strip()
                        return json.loads(text_resp)
                    else:
                        import logging

                        logging.error(
                            f"Ollama vision fallback failed with status {response.status_code}: {response.text}"
                        )
            except Exception as e:
                import logging

                logging.error(
                    f"Ollama vision fallback exception: {e}. Falling back to Gemini."
                )

        # Fallback to Gemini if Ollama fails or isn't configured
        api_key = getattr(settings, "GEMINI_API_KEY", None)
        if not api_key:
            return []

        model = "gemini-2.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": "image/jpeg",
                                "data": base64_image,
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            response_data = response.json()
            text_resp = (
                response_data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "[]")
            )

            text_resp = text_resp.strip()
            if text_resp.startswith("```json"):
                text_resp = text_resp[7:]
            elif text_resp.startswith("```"):
                text_resp = text_resp[3:]
            if text_resp.endswith("```"):
                text_resp = text_resp[:-3]
            text_resp = text_resp.strip()

            return json.loads(text_resp)

    @staticmethod
    async def process_pdf(
        pdf_path: str, total_questions: int = 30, skip_qr: bool = False
    ) -> List[Dict[str, Any]]:
        results = []
        with tempfile.TemporaryDirectory() as path:
            images = convert_from_path(pdf_path, output_folder=path)
            for i, img in enumerate(images):
                img_path = os.path.join(path, f"page_{i}.jpg")
                img.save(img_path, "JPEG")
                result = await OMRCVService.process_image(
                    img_path, total_questions, skip_qr=skip_qr
                )
                results.append(result)
        return results

    @staticmethod
    async def process_zip(
        zip_path: str, total_questions: int = 30, skip_qr: bool = False
    ) -> List[Dict[str, Any]]:
        results = []
        with tempfile.TemporaryDirectory() as extract_dir:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            for root, _, files in os.walk(extract_dir):
                for file in files:
                    ext = file.lower().split(".")[-1]
                    file_path = os.path.join(root, file)
                    if ext in ["jpg", "jpeg", "png"]:
                        result = await OMRCVService.process_image(
                            file_path, total_questions, skip_qr=skip_qr
                        )
                        results.append(result)
                    elif ext == "pdf":
                        pdf_results = await OMRCVService.process_pdf(
                            file_path, total_questions, skip_qr=skip_qr
                        )
                        results.extend(pdf_results)
        return results

import io
import logging
import re

import pdfplumber
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.curriculum import Book, KnowledgeChunk

logger = logging.getLogger(__name__)


try:
    import pytesseract
    from pdf2image import convert_from_bytes

    HAS_OCR = True
except ImportError:
    HAS_OCR = False


def _clean_text(text: str) -> str:
    lines = text.split("\n")
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^\d+$", stripped):
            continue
        if re.match(r"^Page\s*\d+", stripped, re.IGNORECASE):
            continue
        if re.match(r"^-\s*\d+\s*-$", stripped):
            continue
        cleaned.append(stripped)
    text = "\n".join(cleaned)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _estimate_tokens(text: str) -> int:
    return int(len(text.split()) / 0.75)


def _chunk_text(text: str, min_tokens: int = 300, max_tokens: int = 500, overlap_tokens: int = 50) -> list[dict]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[dict] = []
    current_chunk: list[str] = []
    current_token_count = 0

    for para in paragraphs:
        para_tokens = _estimate_tokens(para)

        if current_token_count + para_tokens <= max_tokens:
            current_chunk.append(para)
            current_token_count += para_tokens
        else:
            if current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "token_count": current_token_count,
                    "chunk_index": len(chunks),
                })
                overlap_words: list[str] = []
                overlap_tok = 0
                for p in reversed(current_chunk):
                    p_tok = _estimate_tokens(p)
                    if overlap_tok + p_tok <= overlap_tokens * 2:
                        overlap_words.insert(0, p)
                        overlap_tok += p_tok
                    else:
                        break
                current_chunk = list(overlap_words)
                current_token_count = overlap_tok
            current_chunk.append(para)
            current_token_count += para_tokens

    if current_chunk:
        chunk_text = "\n\n".join(current_chunk)
        chunks.append({
            "text": chunk_text,
            "token_count": current_token_count,
            "chunk_index": len(chunks),
        })

    return chunks


class DocumentAgentResult:
    def __init__(self, success: bool, chunks_created: int = 0, error: str | None = None):
        self.success = success
        self.chunks_created = chunks_created
        self.error = error


class DocumentAgent:
    stage_name = "extracting_text"

    @staticmethod
    def _ocr_page(image: Image.Image) -> str:
        lang = "eng+hin+guj"
        config = "--oem 3 --psm 6"
        try:
            return pytesseract.image_to_string(image, lang=lang, config=config)
        except Exception:
            try:
                return pytesseract.image_to_string(image, lang="eng", config=config)
            except Exception as e:
                logger.warning("OCR failed on a page: %s", e)
                return ""

    @staticmethod
    def _ocr_extract(file_path: str) -> str:
        with open(file_path, "rb") as f:
            pdf_bytes = f.read()
        images = convert_from_bytes(pdf_bytes, dpi=300)
        all_text: list[str] = []
        for img in images:
            text = DocumentAgent._ocr_page(img)
            if text:
                all_text.append(text)
        return "\n".join(all_text)

    async def run(self, db: AsyncSession, book_id: int) -> DocumentAgentResult:
        result = await db.execute(select(Book).where(Book.id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            return DocumentAgentResult(success=False, error=f"Book {book_id} not found")

        file_path = book.file_path
        try:
            text_parts: list[str] = []
            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

            raw_text = "\n".join(text_parts)
            cleaned = _clean_text(raw_text)

            if page_count > 0 and not cleaned:
                if HAS_OCR:
                    logger.info("No selectable text found; falling back to OCR for %s", file_path)
                    ocr_text = self._ocr_extract(file_path)
                    cleaned = _clean_text(ocr_text)
                    if not cleaned:
                        return DocumentAgentResult(
                            success=False,
                            error=f"PDF has {page_count} page(s) but neither text extraction nor OCR produced any content. The images may be low quality or blank.",
                        )
                else:
                    return DocumentAgentResult(
                        success=False,
                        error=f"PDF has {page_count} page(s) but no extractable text. Install OCR dependencies (tesseract-ocr, pytesseract, pdf2image) to enable scanned PDF support.",
                    )

            # Remove previous chunks to avoid duplicates on re-runs
            old = await db.execute(select(KnowledgeChunk).where(KnowledgeChunk.book_id == book_id))
            for old_kc in old.scalars().all():
                await db.delete(old_kc)

            chunks = _chunk_text(cleaned)

            for ch in chunks:
                kc = KnowledgeChunk(
                    book_id=book_id,
                    chunk_text=ch["text"],
                    chunk_index=ch["chunk_index"],
                    token_count=ch["token_count"],
                )
                db.add(kc)

            book.processing_status = "extracted"
            await db.commit()

            return DocumentAgentResult(success=True, chunks_created=len(chunks))

        except FileNotFoundError:
            return DocumentAgentResult(success=False, error=f"PDF file not found at {file_path}")
        except Exception as e:
            await db.rollback()
            logger.exception("Document agent failed for book %d", book_id)
            return DocumentAgentResult(success=False, error=str(e))

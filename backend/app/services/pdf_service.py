import pdfplumber


def extract_text_from_pdf(file_path: str) -> tuple[str, int, int]:
    text_parts = []
    word_count = 0
    page_count = 0
    with pdfplumber.open(file_path) as pdf:
        page_count = len(pdf.pages)
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text_parts.append(page_text)
            word_count += len(page_text.split())
    full_text = "\n".join(text_parts)
    return full_text, page_count, word_count

import asyncio
from app.services.pdf_paper_service import PDFPaperService

def test_pdf():
    pdf_service = PDFPaperService()
    
    paper_info = {
        "name": "Test Paper",
        "grade": 10,
        "subject_id": 1,
        "subject_name": "Maths",
        "total_marks": 100,
        "duration_minutes": 60,
    }
    
    questions = [
        {
            "sequence": 1,
            "question_text_en": "What is 2+2?",
            "options": [
                {"option_text_en": "3", "prefix": "A)"},
                {"option_text_en": "4", "prefix": "B)"},
            ]
        }
    ]
    
    buf = pdf_service.generate_paper_pdf(paper_info, questions, language="english")
    print(f"Generated PDF size: {len(buf.getvalue())} bytes")
    
if __name__ == "__main__":
    test_pdf()

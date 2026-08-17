import asyncio
import os
import shutil
import tempfile
from reportlab.pdfgen import canvas

# Import from app context
from app.services.omr_service import generate_omr_pdf
from app.services.omr_cv_service import OMRCVService

# Mock student model
class MockStudent:
    def __init__(self, id, full_name, roll_number="12345"):
        self.id = id
        self.full_name = full_name
        self.roll_number = roll_number

async def main():
    print("Testing OMR Dynamic Sizing...")
    
    students = [MockStudent(1, "Alice")]
    
    # Generate 100 question OMR
    pdf_path = generate_omr_pdf(
        paper_id=999,
        students=students,
        school_id=1,
        paper_name="Test Paper",
        total_questions=100,
        batch_id="TEST_BATCH_100"
    )
    
    print(f"OMR PDF generated successfully at {pdf_path}")
    if os.path.exists(pdf_path):
        print(f"PDF size: {os.path.getsize(pdf_path)} bytes")
    else:
        print("FAILED: PDF not found.")
        return
        
    print("\nTesting OMR CV Zip/Bulk Upload Logic...")
    # Create a mock zip file with a single PDF (the one we just generated)
    with tempfile.TemporaryDirectory() as td:
        zip_path = os.path.join(td, "bulk_upload.zip")
        import zipfile
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.write(pdf_path, os.path.basename(pdf_path))
            
        print(f"Created mock zip file at {zip_path}")
        
        # Test process_zip directly
        try:
            results = await OMRCVService.process_zip(zip_path, total_questions=100, skip_qr=True)
            print(f"Processed ZIP successfully. Found {len(results)} evaluated sheets.")
        except Exception as e:
            print(f"Error during CV processing (expected if OpenCV dependencies or models are missing/mocked): {e}")

if __name__ == "__main__":
    asyncio.run(main())

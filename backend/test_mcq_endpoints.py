import asyncio
import io
import httpx
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.db.models.auth import User
from app.core.database import async_session_factory
import tempfile


from app.core.deps import get_current_user
from app.db.models.auth import User

def override_get_current_user():
    user = User(id=1, email="test@example.com")
    return user

app.dependency_overrides[get_current_user] = override_get_current_user

async def setup_db():
    from app.core.database import async_session_factory
    from app.db.models.curriculum import Subject
async def run_tests():
    print("--- Starting MCQ Engine Endpoint Tests ---")
    headers = {}
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Test Curriculum Upload
        print("Testing /api/v1/mcq-engine/curriculum ...")
        dummy_curriculum = {"class_name": "Class 10", "subject_id": 1}
        res = await client.post("/api/v1/mcq-engine/curriculum", json=dummy_curriculum, headers=headers)
        print(res.status_code, res.json())
        assert res.status_code == 200
        curriculum_id = res.json()["id"]
        
        # 2. Test Textbook Upload
        print("Testing /api/v1/mcq-engine/textbook ...")
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp.write(b"%PDF-1.4 mock pdf data")
            tmp.seek(0)
            with open(tmp.name, "rb") as f:
                res = await client.post(
                    "/api/v1/mcq-engine/textbook", 
                    files={"file": ("test.pdf", f, "application/pdf")},
                    data={"class_name": "Class 10", "subject_id": 1, "curriculum_id": curriculum_id},
                    headers=headers
                )
        print(res.status_code, res.json())
        assert res.status_code == 200
        textbook_id = res.json()["id"]
        
        # 3. Test Generate Background Job
        print("Testing /api/v1/mcq-engine/generate ...")
        gen_payload = {
            "class_name": "Class 10",
            "subject_id": 1,
            "textbook_id": textbook_id,
            "language": "english"
        }
        res = await client.post("/api/v1/mcq-engine/generate", json=gen_payload, headers=headers)
        print(res.status_code, res.json())
        assert res.status_code == 200
        job_id = res.json()["id"]
        
        print("Waiting for generation job to complete...")
        from app.db.models.mcq_engine import MCQEGenerationJob
        from app.core.database import async_session_factory
        from sqlalchemy.future import select
        
        async def poll_job():
            for _ in range(30):
                async with async_session_factory() as db:
                    result = await db.execute(select(MCQEGenerationJob).where(MCQEGenerationJob.id == job_id))
                    job = result.scalar_one_or_none()
                    if job and job.status in ["completed", "failed"]:
                        return job.status
                await asyncio.sleep(1)
            return "timeout"
            
        status = await poll_job()
        print(f"Job finished with status: {status}")
        
        # 4. Test Paper ZIP Download
        print("Testing /api/v1/mcq-engine/papers/{job_id}/download ...")
        res = await client.get(f"/api/v1/mcq-engine/papers/{job_id}/download", headers=headers)
        print(res.status_code, "Length:", len(res.content))
        
        # 5. Test OMR Upload
        print("Testing /api/v1/mcq-engine/omr/upload ...")
        with tempfile.NamedTemporaryFile(suffix=".png") as tmp:
            tmp.write(b"mock image data")
            tmp.seek(0)
            with open(tmp.name, "rb") as f:
                res = await client.post(
                    "/api/v1/mcq-engine/omr/upload", 
                    files={"file": ("omr.png", f, "image/png")},
                    headers=headers
                )
        print(res.status_code, res.json())
        
        if res.status_code == 200:
            student_result_id = res.json()["student_result_id"]
            # 6. Test Marked Sheet
            print("Testing /api/v1/mcq-engine/student-results/{id}/marked-sheet ...")
            res2 = await client.get(f"/api/v1/mcq-engine/student-results/{student_result_id}/marked-sheet", headers=headers)
            print(res2.status_code, "Length:", len(res2.content))
            
            # 7. Test Concept Analysis
            print("Testing /api/v1/mcq-engine/student-results/{id}/concept-analysis ...")
            res3 = await client.get(f"/api/v1/mcq-engine/student-results/{student_result_id}/concept-analysis", headers=headers)
            print(res3.status_code, "Length:", len(res3.content))

if __name__ == "__main__":
    asyncio.run(run_tests())

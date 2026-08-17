import asyncio
import httpx
import time

async def main():
    base_url = "http://localhost:8000/api/v1"
    
    async with httpx.AsyncClient(timeout=30) as client:
        # Login
        login_res = await client.post(f"{base_url}/auth/login", json={"email": "admin@gseb.org", "password": "Admin@123"})
        if login_res.status_code != 200:
            print("Login failed:", login_res.status_code, login_res.text)
            return
        token = login_res.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        payload = {
            "grade": 10,
            "subject_id": 2,
            "chapter_ids": [4],
            "total_questions": 10,
            "difficulty": "medium",
            "bloom_level": "understand",
            "num_sets": 2
        }
        
        print("Starting custom generation...")
        res = await client.post(f"{base_url}/papers/custom-generate", json=payload, headers=headers)
        if res.status_code != 200:
            print("Failed custom generate:", res.status_code, res.text)
            return
            
        job = res.json()
        print("Job started:", job)
        job_id = job.get("job_id")
        
        while True:
            res = await client.get(f"{base_url}/papers/custom-generate/jobs/{job_id}", headers=headers)
            if res.status_code != 200:
                print("Failed status fetch:", res.status_code, res.text)
                return
            status = res.json()
            print("Job status:", status["status"], status.get("progress", 0))
            if status["status"] == "failed":
                print("Generation failed")
                return
            if status["status"] == "completed":
                print("Final result:", status)
                break
            time.sleep(2)
        
        # Test fetching the single paper to verify blueprint_id is returned
        params = status.get("params", "{}")
        if isinstance(params, str):
            import json
            params = json.loads(params)
        paper_ids = params.get("paper_ids", [])
        if not paper_ids:
            print("No paper IDs returned.")
            return
        paper_id = paper_ids[0]
        
        print(f"Fetching paper_id {paper_id}...")
        res = await client.get(f"{base_url}/papers/{paper_id}", headers=headers)
        if res.status_code != 200:
            print("Failed fetching single paper:", res.status_code, res.text)
            return
        paper_detail = res.json()
        print("Paper Detail blueprint_id:", paper_detail.get("blueprint_id"))
        if paper_detail.get("blueprint_id"):
            print("SUCCESS: blueprint_id is present.")
        else:
            print("FAILED: blueprint_id is missing.")
            
if __name__ == "__main__":
    asyncio.run(main())

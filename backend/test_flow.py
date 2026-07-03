import requests
import json

API_URL = "http://localhost:8000/api/v1"

def run_test():
    print("1. Logging in...")
    resp = requests.post(f"{API_URL}/auth/login", json={
        "email": "admin@gseb.org",
        "password": "Admin@123"
    })
    
    if resp.status_code != 200:
        print("Login failed:", resp.text)
        return
        
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    book_id = 6
    print(f"2. Generating Questions for Book ID {book_id}...")
    resp = requests.post(
        f"{API_URL}/chapters/{book_id}/generate-questions?count=3&bloom_level=understand&difficulty=medium&question_type=mcq", 
        headers=headers
    )
    if resp.status_code == 200:
        print("Generated Questions:")
        print(json.dumps(resp.json(), indent=2))
    else:
        print("Failed to generate questions:", resp.text)

if __name__ == "__main__":
    run_test()

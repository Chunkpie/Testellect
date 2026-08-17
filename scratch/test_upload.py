import requests

url = "http://localhost:8000/api/v1/auth/login"
resp = requests.post(url, json={"email": "r.sharma@gseb.org", "password": "Teacher@123"})
token = resp.json()["access_token"]

url = "http://localhost:8000/api/v1/omr/SESSION_1783757693099/scan-upload"
files = {'files': open('C:\\Users\\lenovo\\.gemini\\antigravity\\brain\\0b3195bd-4bdf-4f9b-a89c-177f61d6366d\\media__1783751654624.jpg', 'rb')}
headers = {"Authorization": f"Bearer {token}"}
r = requests.post(url, headers=headers, files=files)
print(r.status_code)
print(r.json())

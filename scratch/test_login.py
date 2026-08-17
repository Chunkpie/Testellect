import requests; print(requests.post('http://localhost:8000/api/v1/auth/login', json={'email': 'r.sharma@gseb.org', 'password': 'Teacher@123'}).json())

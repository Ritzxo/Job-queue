import httpx

for i in range(1, 11):
    response = httpx.post("http://127.0.0.1:8000/jobs", json={"payload": f"job {i}"})
    print(response.status_code, response.json()["id"])
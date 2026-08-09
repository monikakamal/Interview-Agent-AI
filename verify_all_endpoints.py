"""
Verification script testing all required FastAPI endpoints:
- GET /
- GET /health
- POST /api/interview
- GET /docs
- GET /openapi.json
"""

import sys
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def verify():
    print("==================================================")
    print(" VERIFYING ALL FASTAPI ENDPOINTS REACHABILITY")
    print("==================================================")

    # 1. GET /
    res_root = client.get("/")
    print(f"1. GET /                -> Status: {res_root.status_code}")
    assert res_root.status_code == 200, f"GET / failed with status {res_root.status_code}"

    # 2. GET /health
    res_health = client.get("/health")
    print(f"2. GET /health          -> Status: {res_health.status_code}, Body: {res_health.json()}")
    assert res_health.status_code == 200, f"GET /health failed with status {res_health.status_code}"

    # 3. GET /docs
    res_docs = client.get("/docs")
    print(f"3. GET /docs            -> Status: {res_docs.status_code}")
    assert res_docs.status_code == 200, f"GET /docs failed with status {res_docs.status_code}"

    # 4. GET /openapi.json
    res_openapi = client.get("/openapi.json")
    print(f"4. GET /openapi.json    -> Status: {res_openapi.status_code}")
    assert res_openapi.status_code == 200, f"GET /openapi.json failed with status {res_openapi.status_code}"

    # 5. POST /api/interview (Initial Start)
    start_payload = {
        "sessionId": "verify-session-001",
        "candidateId": "CAND-001"
    }
    res_start = client.post("/api/interview", json=start_payload)
    print(f"5a. POST /api/interview  -> Status: {res_start.status_code}")
    assert res_start.status_code == 200, f"POST /api/interview failed with status {res_start.status_code}"
    start_json = res_start.json()
    assert start_json["done"] is False
    assert "reply" in start_json

    # 6. POST /api/interview (Turn Request)
    turn_payload = {
        "sessionId": "verify-session-001",
        "message": "We built a vector search pipeline using dense embeddings and Cosine similarity for semantic retrieval."
    }
    res_turn = client.post("/api/interview", json=turn_payload)
    print(f"5b. POST /api/interview (Turn) -> Status: {res_turn.status_code}")
    assert res_turn.status_code == 200, f"POST /api/interview (Turn) failed with status {res_turn.status_code}"
    turn_json = res_turn.json()
    assert "reply" in turn_json

    # 7. POST /api/interview/ (Trailing Slash Support with fresh session)
    start_payload_2 = {
        "sessionId": "verify-session-002",
        "candidateId": "CAND-001"
    }
    res_slash = client.post("/api/interview/", json=start_payload_2)
    print(f"5c. POST /api/interview/ (Slash) -> Status: {res_slash.status_code}")
    assert res_slash.status_code == 200, f"POST /api/interview/ failed with status {res_slash.status_code}"

    print("==================================================")
    print(" ALL 5 ENDPOINTS VERIFIED AND WORKING 100%! ")
    print("==================================================")

if __name__ == "__main__":
    verify()

"""
Integration tests for FastAPI endpoints matching the Technical Specification contract.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_start_interview_with_candidate_id():
    payload = {
        "sessionId": "test-session-001",
        "candidateId": "CAND-001"
    }
    response = client.post("/api/interview", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "reply" in data
    assert data["done"] is False
    assert "Welcome" in data["reply"] or "interview" in data["reply"].lower()


def test_interview_missing_session_id():
    payload = {
        "candidateId": "mem_01"
    }
    response = client.post("/api/interview", json=payload)
    assert response.status_code == 400


def test_interview_invalid_candidate_id():
    payload = {
        "sessionId": "test-session-invalid",
        "candidateId": "non_existent_id_999"
    }
    response = client.post("/api/interview", json=payload)
    assert response.status_code == 404

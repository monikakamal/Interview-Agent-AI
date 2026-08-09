"""
Integration test verifying POST /api/interview with inline candidate dictionary payload,
following multi-turn conversation to completion.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_candidate_dict_payload_flow():
    session_id = "test123"

    candidate_dict = {
        "member": {
            "id": "CAND-DICT-001",
            "name": "Jane Doe",
            "jobRole": "Senior AI Architect",
            "yearsExperience": 7,
            "education": "MS AI",
            "status": "ACTIVE"
        },
        "missions": [
            {"day": 7, "title": "Embeddings Explained", "passed": True, "attempts": 1},
            {"day": 8, "title": "Vector Databases Overview", "passed": True, "attempts": 1},
            {"day": 10, "title": "Retrieval Engine", "passed": True, "attempts": 1},
            {"day": 12, "title": "Prompt Engineering", "passed": True, "attempts": 1},
            {"day": 16, "title": "Chatbot Build", "passed": True, "attempts": 1},
            {"day": 23, "title": "MCP Tools", "passed": True, "attempts": 1}
        ],
        "signals": {
            "commitDays": 15,
            "missionsCompleted": 6,
            "missionsFirstTry": 6
        }
    }

    # Turn 1: Initialize session with inline candidate dict
    payload_init = {
        "sessionId": session_id,
        "candidate": candidate_dict
    }

    res_init = client.post("/api/interview", json=payload_init)
    print(f"Turn 1 Start Status: {res_init.status_code}")
    assert res_init.status_code == 200, f"Expected 200 OK, got {res_init.status_code}: {res_init.text}"

    data_init = res_init.json()
    assert data_init["done"] is False
    assert "reply" in data_init
    assert "Jane Doe" in data_init["reply"] or "Welcome" in data_init["reply"]

    # Turns 2..N: Conduct conversation turns until completed
    sample_turns = [
        "In our system we setup virtualenv and Pylance to isolate dependencies and maintain clean Python packages.",
        "We built a dataset cleaning pipeline using pandas and numpy to handle missing values and schema validation.",
        "For semantic search, we computed dense vector embeddings using neural embedding models and indexed them in a vector database.",
        "Vector search achieves low-latency top-k retrieval using HNSW indexes and cosine similarity matching.",
        "Prompt engineering strategies include role instruction, context injection, structural constraints, and few-shot examples.",
        "Fine-tuning adjusts model parameters using LoRA parameter efficient tuning while monitoring evaluation metrics.",
        "We built a chatbot backend using FastAPI, stateful session memory, and streaming responses.",
        "Agentic AI utilizes tool calling and Model Context Protocol to connect LLMs to external APIs and SQL databases.",
        "Evaluation measures semantic accuracy, precision, latency benchmarks, and safety filters prior to production deployment.",
        "In production we configure rate limiting, circuit breakers, fallback engines, and structured logging for observability.",
        "To optimize latency, we implement vector caching and async database queries across microservices.",
        "We handle edge cases by implementing strict input validation and graceful fallback responses.",
    ]

    is_done = False
    final_feedback = None

    for idx, msg in enumerate(sample_turns, 2):
        turn_res = client.post("/api/interview", json={"sessionId": session_id, "message": msg})
        assert turn_res.status_code == 200, f"Turn {idx} failed with status {turn_res.status_code}: {turn_res.text}"
        data = turn_res.json()

        if data["done"] is True:
            is_done = True
            final_feedback = data.get("feedback")
            print(f"Interview completed at turn {idx}!")
            break

    assert is_done is True, "Interview did not complete within the turn limit"
    assert final_feedback is not None, "Final feedback payload missing"
    assert "summary" in final_feedback
    assert isinstance(final_feedback["strengths"], list)
    assert isinstance(final_feedback["gaps"], list)
    assert isinstance(final_feedback["next"], list)
    assert len(final_feedback["strengths"]) > 0

    print("Candidate dict flow integration test passed successfully!")


if __name__ == "__main__":
    test_candidate_dict_payload_flow()

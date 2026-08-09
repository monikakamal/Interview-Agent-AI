"""
Full end-to-end interview flow integration test.
Tests initializing session, submitting multi-turn candidate responses, adaptive probing,
and verifying completion with final feedback payload.
"""

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_interview_flow():
    session_id = "e2e-interview-session-999"

    # Turn 1: Start interview
    init_res = client.post("/api/interview", json={"sessionId": session_id, "candidateId": "CAND-001"})
    assert init_res.status_code == 200
    init_data = init_res.json()
    assert init_data["done"] is False
    assert len(init_data["reply"]) > 10

    # Substantive responses demonstrating technical depth and examples
    substantive_answers = [
        "In our AI project we configured VS Code with Pylance and Python virtual environments (.venv) to isolate dependencies and enforce clean imports.",
        "We built a data foundations pipeline using Pandas and NumPy to clean raw json datasets, handling missing values and structural normalization.",
        "For embeddings, we computed dense vector representations using neural embedding models and indexed them in a vector database for semantic retrieval.",
        "Vector search allows top-k retrieval using cosine similarity and HNSW vector index for low-latency similarity queries in RAG architectures.",
        "Prompt engineering involves constructing clear role instructions, system prompts, context injection, and few-shot examples.",
        "Fine-tuning adapts LLM weights to specific domain tasks using LoRA or QLoRA parameter efficient methods while monitoring evaluation metrics.",
        "We built a multi-turn chatbot application using FastAPI backend, stateful session memory, and streaming responses.",
        "Agentic AI utilizes tool calling and model context protocol (MCP) to allow LLMs to interact with external databases and microservice APIs.",
        "For evaluation, we measure semantic accuracy, retrieval precision, latency, and toxicity benchmarks prior to production deployment.",
        "In production, we configure rate limiting, circuit breakers, fallback model engines, and structured logging for observability.",
        "To optimize latency, we implement vector caching and async database queries across our microservices.",
        "We handle edge cases by implementing strict input validation and graceful fallback responses when model quota is exhausted.",
        "For system design trade-offs, we balance embedding vector dimensions against memory storage footprint and query latency.",
        "Finally, we run automated unit and integration tests across our FastAPI routes to verify system reliability.",
    ]

    is_done = False
    final_feedback = None

    for idx, answer in enumerate(substantive_answers, 1):
        turn_res = client.post("/api/interview", json={"sessionId": session_id, "message": answer})
        assert turn_res.status_code == 200
        data = turn_res.json()

        if data["done"] is True:
            is_done = True
            final_feedback = data.get("feedback")
            break

    # Verify interview completed and generated valid structured feedback
    assert is_done is True
    assert final_feedback is not None
    assert "summary" in final_feedback
    assert isinstance(final_feedback["strengths"], list)
    assert isinstance(final_feedback["gaps"], list)
    assert isinstance(final_feedback["next"], list)
    assert len(final_feedback["strengths"]) > 0
    assert len(final_feedback["next"]) > 0

"""
Tests for AnswerEvaluator multi-dimensional scoring and FeedbackEngine.
"""

from agents.evaluator import AnswerEvaluator
from agents.planner import PlannedQuestion
from memory.session_memory import SessionMemory
from rag.retriever import RAGRetriever
from agents.feedback import FeedbackEngine


def test_answer_evaluator_dimensions():
    evaluator = AnswerEvaluator()
    question = PlannedQuestion(
        question_id="test_q1",
        day=7,
        topic="Embeddings & Vector Search",
        question_type="engineering",
        prompt_template="Explain vector search trade-offs",
    )

    strong_answer = (
        "We use vector embeddings created by dense neural models to convert text into fixed-size "
        "numerical vectors. For vector retrieval, we build an HNSW vector index which trade off "
        "memory usage for low-latency top-k cosine similarity queries. For example, in a RAG pipeline, "
        "this reduces search latency from O(N) to O(log N) while preserving recall."
    )

    eval_result = evaluator.evaluate_answer(question, strong_answer)

    assert eval_result.score >= 3.5
    assert eval_result.dimensions.correctness >= 3.5
    assert eval_result.dimensions.depth >= 3.5
    assert eval_result.dimensions.examples >= 3.5
    assert eval_result.level in ["good", "strong", "excellent"]


def test_answer_evaluator_weak_answer():
    evaluator = AnswerEvaluator()
    question = PlannedQuestion(
        question_id="test_q2",
        day=1,
        topic="Python Environment",
        question_type="conceptual",
        prompt_template="What is a virtualenv?",
    )

    weak_answer = "i think python is good"
    eval_result = evaluator.evaluate_answer(question, weak_answer)

    assert eval_result.score < 3.0
    assert eval_result.needs_follow_up is True
    assert len(eval_result.gaps) > 0


def test_feedback_engine_generation():
    retriever = RAGRetriever()
    candidate = retriever.get_candidate("CAND-001")
    assert candidate is not None

    session = SessionMemory(session_id="test_session", candidate=candidate)
    session.record_asked_question("q1", 7, "Embeddings", "Explain embeddings")
    session.update_latest_answer_and_eval(
        answer_text="Vector embeddings represent text as dense vectors for semantic similarity.",
        score=4.2,
        level="strong",
        strengths=["Good technical terminology"],
        gaps=[],
    )

    feedback_engine = FeedbackEngine()
    payload = feedback_engine.generate_feedback(session)

    assert payload.summary is not None
    assert isinstance(payload.strengths, list)
    assert isinstance(payload.gaps, list)
    assert isinstance(payload.next, list)
    assert len(payload.strengths) > 0
    assert len(payload.next) > 0

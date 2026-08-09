"""
Master test runner executing all unit and integration test suites.
"""

import sys

def main():
    print("==================================================")
    print(" Running AI Interview Agent Test Suite")
    print("==================================================")

    # 1. Retrieval Tests
    try:
        import tests.test_retrieval as tr
        tr.test_loader_chunking()
        tr.test_embedding_service()
        tr.test_rag_retriever_top_k()
        tr.test_candidate_progress_retrieval()
        print("✓ RAG Retrieval Tests Passed")
    except Exception as exc:
        print(f"✗ RAG Retrieval Tests Failed: {exc}")
        sys.exit(1)

    # 2. Evaluation Tests
    try:
        import tests.test_evaluation as te
        te.test_answer_evaluator_dimensions()
        te.test_answer_evaluator_weak_answer()
        te.test_feedback_engine_generation()
        print("✓ Answer Evaluator & Feedback Engine Tests Passed")
    except Exception as exc:
        print(f"✗ Answer Evaluation Tests Failed: {exc}")
        sys.exit(1)

    # 3. API Contract Tests
    try:
        import tests.test_api as ta
        ta.test_health_endpoint()
        ta.test_start_interview_with_candidate_id()
        ta.test_interview_missing_session_id()
        ta.test_interview_invalid_candidate_id()
        print("✓ API Endpoint & Specification Tests Passed")
    except Exception as exc:
        print(f"✗ API Tests Failed: {exc}")
        sys.exit(1)

    # 4. E2E Interview Flow Tests
    try:
        import tests.test_interview_flow as tif
        tif.test_full_interview_flow()
        print("✓ End-to-End Multi-Turn Interview Flow Tests Passed")
    except Exception as exc:
        print(f"✗ E2E Interview Flow Tests Failed: {exc}")
        sys.exit(1)

    print("==================================================")
    print(" ALL TESTS PASSED SUCCESSFULLY! (4/4)")
    print("==================================================")

if __name__ == "__main__":
    main()

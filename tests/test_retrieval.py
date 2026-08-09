"""
Tests for RAG Loader, Embedding Service, and Vector Retriever.
"""

from pathlib import Path
from rag.embeddings import EmbeddingService
from rag.loader import DataLoader
from rag.retriever import RAGRetriever


def test_loader_chunking():
    base_dir = Path(__file__).resolve().parent.parent
    c_path = base_dir / "data" / "candidates.json"
    curr_path = base_dir / "data" / "curriculum.json"

    loader = DataLoader(candidates_path=c_path, curriculum_path=curr_path)
    curriculum = loader.load_curriculum()
    assert curriculum is not None
    assert len(curriculum.days) > 0

    chunks = loader.chunk_curriculum()
    assert len(chunks) > len(curriculum.days)
    assert any(c.chunk_type == "overview" for c in chunks)
    assert any(c.chunk_type == "objective" for c in chunks)


def test_embedding_service():
    service = EmbeddingService()
    corpus = [
        "Vector embeddings and RAG retrieval systems.",
        "FastAPI Python server for web APIs.",
        "Agentic AI workflow and tool calling.",
    ]
    service.fit(corpus)

    vec1 = service.embed_text("Vector embedding search")
    vec2 = service.embed_text("FastAPI web server")
    vec3 = service.embed_text("RAG retrieval embeddings")

    sim1_3 = service.cosine_similarity(vec1, vec3)
    sim1_2 = service.cosine_similarity(vec1, vec2)

    assert vec1.shape[0] > 0
    assert sim1_3 > sim1_2


def test_rag_retriever_top_k():
    retriever = RAGRetriever()
    results = retriever.search_top_k(query="embeddings and vector search", top_k=3)
    assert len(results) <= 3
    assert len(results) > 0
    top_chunk, score = results[0]
    assert top_chunk.content is not None
    assert score >= 0.0


def test_candidate_progress_retrieval():
    retriever = RAGRetriever()
    candidate = retriever.get_candidate("CAND-001")
    assert candidate is not None

    completed = retriever.get_completed_days(candidate)
    skipped = retriever.get_skipped_days(candidate)
    relevant = retriever.get_relevant_curriculum_days(candidate)

    # Check skipped days are excluded from completed
    for s in skipped:
        assert s not in completed

    # Relevant curriculum days should contain at least 4 days
    assert len(relevant) >= 4

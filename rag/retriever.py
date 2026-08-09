"""
RAG Retriever with vector similarity search, chunking, and candidate progress filtering.
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

from models.schemas import CandidateProfile, CurriculumDay
from rag.embeddings import EmbeddingService
from rag.loader import CurriculumChunk, DataLoader
from utils.logger import logger


class RAGRetriever:
    """
    RAG Retriever for indexing curriculum chunks, performing vector similarity search,
    and injecting relevant curriculum context into interview generation.
    """

    def __init__(
        self,
        candidates_path: Optional[Path] = None,
        curriculum_path: Optional[Path] = None,
    ) -> None:
        base_dir = Path(__file__).resolve().parent.parent
        self.candidates_path = candidates_path or (base_dir / "data" / "candidates.json")
        self.curriculum_path = curriculum_path or (base_dir / "data" / "curriculum.json")

        self.loader = DataLoader(
            candidates_path=self.candidates_path,
            curriculum_path=self.curriculum_path,
        )

        self.embedding_service = EmbeddingService()
        self.chunks: List[CurriculumChunk] = []
        self.vectors: Dict[str, np.ndarray] = {}
        self.curriculum_data = None

        self._build_vector_index()

    def _build_vector_index(self) -> None:
        """
        Loads curriculum data, generates semantic chunks, fits TF-IDF vectorizer,
        and builds vector embeddings index.
        """
        try:
            self.curriculum_data = self.loader.load_curriculum()
            self.chunks = self.loader.chunk_curriculum()

            corpus = [c.content for c in self.chunks]
            self.embedding_service.fit(corpus)

            for chunk in self.chunks:
                self.vectors[chunk.chunk_id] = self.embedding_service.embed_text(chunk.content)

            logger.info(
                f"RAG Index initialized: {len(self.chunks)} chunks across "
                f"{len(self.curriculum_data.days)} curriculum days."
            )
        except Exception as exc:
            logger.error(f"Error building RAG vector index: {exc}")

    def get_candidate(self, candidate_id: str) -> Optional[CandidateProfile]:
        """Fetch candidate profile by candidate ID."""
        return self.loader.get_candidate_by_id(candidate_id)

    def get_completed_days(self, candidate: CandidateProfile) -> List[int]:
        """Return curriculum days passed and not skipped."""
        completed = []
        for m in candidate.missions:
            if m.passed is True and m.skipped is not True:
                completed.append(m.day)
        return sorted(set(completed))

    def get_skipped_days(self, candidate: CandidateProfile) -> List[int]:
        """Return curriculum days explicitly marked skipped."""
        skipped = []
        for m in candidate.missions:
            if m.skipped is True:
                skipped.append(m.day)
        return sorted(set(skipped))

    def get_attempted_days(self, candidate: CandidateProfile) -> List[int]:
        """Return curriculum days attempted."""
        attempted = []
        for m in candidate.missions:
            if m.attempts is not None and m.attempts > 0:
                attempted.append(m.day)
        return sorted(set(attempted))

    def get_relevant_curriculum_days(
        self,
        candidate: CandidateProfile,
        exclude_days: Optional[List[int]] = None,
    ) -> List[CurriculumDay]:
        """
        Returns relevant CurriculumDay objects for candidate.
        Priority:
        1. Completed days
        2. Attempted days
        3. Remaining non-skipped days

        Skipped days are strictly excluded.
        """
        exclude = set(exclude_days or [])
        skipped = set(self.get_skipped_days(candidate))
        completed = self.get_completed_days(candidate)
        attempted = self.get_attempted_days(candidate)

        priority_day_nums: List[int] = []

        for d in completed:
            if d not in exclude and d not in skipped:
                priority_day_nums.append(d)

        for d in attempted:
            if d not in exclude and d not in skipped and d not in priority_day_nums:
                priority_day_nums.append(d)

        # Fallback: remaining curriculum days if candidate has fewer than 4 priority days
        if len(priority_day_nums) < 4:
            for day_obj in self.curriculum_data.days:
                d = day_obj.day
                if d not in exclude and d not in skipped and d not in priority_day_nums:
                    priority_day_nums.append(d)

        day_dict = {day_obj.day: day_obj for day_obj in self.curriculum_data.days}
        return [day_dict[d] for d in priority_day_nums if d in day_dict]

    def search_top_k(
        self,
        query: str,
        top_k: int = 3,
        exclude_days: Optional[List[int]] = None,
        only_days: Optional[List[int]] = None,
    ) -> List[Tuple[CurriculumChunk, float]]:
        """
        Performs vector similarity top-k search over curriculum chunks.
        Supports filtering by allowed or excluded curriculum days.
        """
        if not query or not query.strip() or not self.chunks:
            return []

        exclude_set = set(exclude_days or [])
        only_set = set(only_days) if only_days is not None else None

        query_vec = self.embedding_service.embed_text(query)
        scored_chunks: List[Tuple[CurriculumChunk, float]] = []

        for chunk in self.chunks:
            if chunk.day in exclude_set:
                continue
            if only_set is not None and chunk.day not in only_set:
                continue

            chunk_vec = self.vectors.get(chunk.chunk_id)
            if chunk_vec is None:
                continue

            score = self.embedding_service.cosine_similarity(query_vec, chunk_vec)
            scored_chunks.append((chunk, score))

        scored_chunks.sort(key=lambda item: item[1], reverse=True)
        return scored_chunks[:top_k]

    def get_context_for_day(self, day: int) -> str:
        """
        Constructs rich RAG context text for a specific curriculum day.
        """
        day_chunks = [c for c in self.chunks if c.day == day]
        if not day_chunks:
            return f"Curriculum Day {day} context unavailable."

        overview = next((c.content for c in day_chunks if c.chunk_type == "overview"), "")
        tools = next((c.content for c in day_chunks if c.chunk_type == "tool"), "")
        objectives = [c.content for c in day_chunks if c.chunk_type == "objective"]

        context_lines = [f"=== RAG CONTEXT FOR CURRICULUM DAY {day} ==="]
        if overview:
            context_lines.append(overview)
        if tools:
            context_lines.append(tools)
        if objectives:
            context_lines.append("Objectives:\n" + "\n".join(f"- {o}" for o in objectives))

        return "\n".join(context_lines)

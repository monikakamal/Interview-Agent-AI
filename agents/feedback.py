"""
Feedback Engine responsible for generating the final candidate feedback payload
matching the exact schema required by the Technical Specification.
"""

from typing import List, Set

from memory.session_memory import SessionMemory, TurnRecord
from models.schemas import CandidateProfile, FeedbackPayload
from utils.logger import logger


class FeedbackEngine:
    """
    Generates structured final assessment feedback payload for the completed interview.
    """

    def generate_feedback(self, session: SessionMemory) -> FeedbackPayload:
        """
        Generates final FeedbackPayload containing summary, strengths, gaps, and next steps.
        """
        candidate = session.candidate
        candidate_name = candidate.member.name
        turns = session.turns
        avg_score = session.average_score
        total_questions = len([t for t in turns if t.answer_text])

        summary = self._build_summary(candidate_name, total_questions, avg_score, session.covered_concepts, session.weak_concepts)
        strengths = self._build_strengths(turns, session.covered_concepts, avg_score)
        gaps = self._build_gaps(turns, session.weak_concepts)
        next_steps = self._build_next_steps(session.weak_concepts, session.covered_days, avg_score)

        return FeedbackPayload(
            summary=summary,
            strengths=strengths,
            gaps=gaps,
            next=next_steps,
        )

    def _build_summary(
        self,
        candidate_name: str,
        total_questions: int,
        avg_score: float,
        covered_concepts: List[str],
        weak_concepts: List[str],
    ) -> str:
        level = "excellent" if avg_score >= 4.5 else "strong" if avg_score >= 4.0 else "good" if avg_score >= 3.0 else "developing" if avg_score >= 2.0 else "needs improvement"
        
        return (
            f"Candidate {candidate_name} completed {total_questions} evaluated questions across "
            f"{len(covered_concepts)} core curriculum topics with an overall score of {avg_score:.2f}/5.00 ({level}). "
            f"The interview highlighted solid performance in topics such as {', '.join(covered_concepts[:2]) if covered_concepts else 'general concepts'}, "
            f"with targeted growth opportunities identified in {', '.join(weak_concepts[:2]) if weak_concepts else 'advanced trade-off discussions'}."
        )

    def _build_strengths(self, turns: List[TurnRecord], covered_concepts: List[str], avg_score: float) -> List[str]:
        strengths: Set[str] = set()

        for t in turns:
            if t.score is not None and t.score >= 3.5:
                for s in t.strengths:
                    strengths.add(s)

        if not strengths:
            strengths.add("Demonstrated active engagement throughout the technical evaluation.")
            strengths.add("Communicated approach clearly when answering questions.")

        if avg_score >= 4.0:
            strengths.add("Demonstrated strong architectural and engineering principles.")

        return list(strengths)[:6]

    def _build_gaps(self, turns: List[TurnRecord], weak_concepts: List[str]) -> List[str]:
        gaps: Set[str] = set()

        for concept in weak_concepts:
            gaps.add(f"Needs deeper mastery and practice in {concept}.")

        for t in turns:
            if t.score is not None and t.score < 3.5:
                for g in t.gaps:
                    gaps.add(g)

        if not gaps:
            gaps.add("No critical gaps identified; focus on advanced system optimization.")

        return list(gaps)[:6]

    def _build_next_steps(self, weak_concepts: List[str], covered_days: Set[int], avg_score: float) -> List[str]:
        next_steps: List[str] = []

        for concept in weak_concepts:
            next_steps.append(f"Revisit curriculum topics on {concept} and implement hands-on code examples.")

        if covered_days:
            days_str = ", ".join(f"Day {d}" for d in sorted(covered_days)[:3])
            next_steps.append(f"Review core mission objectives from {days_str}.")

        if avg_score < 3.5:
            next_steps.append("Practice explaining engineering trade-offs, edge cases, and performance implications.")

        next_steps.append("Build a end-to-end production capstone project incorporating stateful agents and RAG.")

        return list(dict.fromkeys(next_steps))[:6]

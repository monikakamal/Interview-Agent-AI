"""
Answer Evaluator that multi-dimensionally assesses candidate responses across:
1. Correctness
2. Depth
3. Clarity
4. Examples
5. Terminology
6. Confidence
"""

from dataclasses import dataclass, field
import json
import re
from typing import Dict, List, Optional, Set, Tuple

from agents.planner import PlannedQuestion
from models.schemas import CandidateProfile
from utils.constants import (
    HIGH_SCORE_THRESHOLD,
    LOW_SCORE_THRESHOLD,
    SCORE_WEIGHT_CLARITY,
    SCORE_WEIGHT_CONFIDENCE,
    SCORE_WEIGHT_CORRECTNESS,
    SCORE_WEIGHT_DEPTH,
    SCORE_WEIGHT_EXAMPLES,
    SCORE_WEIGHT_TERMINOLOGY,
)
from utils.logger import logger


@dataclass
class DimensionalScore:
    """
    Sub-scores across 6 technical evaluation dimensions.
    """

    correctness: float  # 0.0 - 5.0
    depth: float        # 0.0 - 5.0
    clarity: float      # 0.0 - 5.0
    examples: float     # 0.0 - 5.0
    terminology: float  # 0.0 - 5.0
    confidence: float   # 0.0 - 5.0


@dataclass
class AnswerEvaluation:
    """
    Evaluation result for an individual candidate answer.
    """

    question_id: str
    day: int
    topic: str
    score: float
    level: str  # "weak", "developing", "good", "strong", "excellent"
    dimensions: DimensionalScore
    strengths: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    needs_follow_up: bool = False
    follow_up_reason: Optional[str] = None
    answered: bool = True
    answer_length: int = 0


class AnswerEvaluator:
    """
    Evaluates candidate responses during technical interview turns.
    Integrates multi-dimensional criteria scoring and follow-up decision logic.
    """

    MIN_MEANINGFUL_LENGTH = 15

    def __init__(self, candidate: Optional[CandidateProfile] = None) -> None:
        self.candidate = candidate

    def evaluate_answer(
        self,
        question: PlannedQuestion,
        answer: str,
        rag_context: str = "",
    ) -> AnswerEvaluation:
        """
        Evaluates a candidate's answer across all 6 technical dimensions.
        """
        cleaned_answer = self._clean_answer(answer)
        if not cleaned_answer or len(cleaned_answer) < self.MIN_MEANINGFUL_LENGTH:
            return AnswerEvaluation(
                question_id=question.question_id,
                day=question.day,
                topic=question.topic,
                score=0.0,
                level="weak",
                dimensions=DimensionalScore(0, 0, 0, 0, 0, 0),
                strengths=[],
                gaps=["Response was missing or too brief to evaluate."],
                needs_follow_up=True,
                follow_up_reason="Candidate provided an incomplete or empty response.",
                answered=False,
                answer_length=len(cleaned_answer),
            )

        answer_lower = cleaned_answer.lower()

        # Dimension 1: Correctness & Technical Soundness
        correctness_score = self._score_correctness(answer_lower, question, rag_context)

        # Dimension 2: Depth & Explanation of Trade-offs
        depth_score = self._score_depth(answer_lower, cleaned_answer)

        # Dimension 3: Clarity & Structure
        clarity_score = self._score_clarity(cleaned_answer)

        # Dimension 4: Concrete Examples & Implementation
        examples_score = self._score_examples(answer_lower)

        # Dimension 5: Technical Terminology & Vocabulary
        terminology_score = self._score_terminology(answer_lower, question.topic)

        # Dimension 6: Confidence & Reasoning
        confidence_score = self._score_confidence(answer_lower)

        dimensions = DimensionalScore(
            correctness=correctness_score,
            depth=depth_score,
            clarity=clarity_score,
            examples=examples_score,
            terminology=terminology_score,
            confidence=confidence_score,
        )

        # Calculate weighted final score (0.0 - 5.0 scale)
        composite_score = (
            correctness_score * SCORE_WEIGHT_CORRECTNESS +
            depth_score * SCORE_WEIGHT_DEPTH +
            clarity_score * SCORE_WEIGHT_CLARITY +
            examples_score * SCORE_WEIGHT_EXAMPLES +
            terminology_score * SCORE_WEIGHT_TERMINOLOGY +
            confidence_score * SCORE_WEIGHT_CONFIDENCE
        )

        final_score = round(max(0.0, min(5.0, composite_score)), 2)
        level = self._get_level(final_score)

        strengths, gaps = self._derive_feedback_notes(dimensions, question.topic)

        needs_follow_up, reason = self._determine_follow_up(
            final_score=final_score,
            question=question,
            answer=cleaned_answer,
            dimensions=dimensions,
        )

        return AnswerEvaluation(
            question_id=question.question_id,
            day=question.day,
            topic=question.topic,
            score=final_score,
            level=level,
            dimensions=dimensions,
            strengths=strengths,
            gaps=gaps,
            needs_follow_up=needs_follow_up,
            follow_up_reason=reason,
            answered=True,
            answer_length=len(cleaned_answer),
        )

    def _score_correctness(self, answer_lower: str, question: PlannedQuestion, rag_context: str) -> float:
        score = 2.5  # Base neutral score
        tokens = set(re.findall(r"\b\w+\b", question.topic.lower()))
        matched_tokens = sum(1 for t in tokens if t in answer_lower and len(t) > 3)

        if matched_tokens > 0:
            score += 1.0

        if len(answer_lower) > 80:
            score += 1.0

        # Check for hedge words that indicate total uncertainty
        if any(w in answer_lower for w in ["dont know", "don't know", "no idea", "not sure at all", "clueless"]):
            score = 1.0

        return min(5.0, score)

    def _score_depth(self, answer_lower: str, answer_orig: str) -> float:
        depth_indicators = {
            "because", "therefore", "reason", "tradeoff", "trade-off",
            "advantage", "disadvantage", "limitation", "however", "depends",
            "architecture", "pipeline", "performance", "scalability", "latency"
        }
        matches = sum(1 for term in depth_indicators if term in answer_lower)

        if len(answer_orig) > 250 and matches >= 3:
            return 5.0
        elif len(answer_orig) > 150 or matches >= 2:
            return 4.0
        elif matches >= 1:
            return 3.0
        return 2.0

    def _score_clarity(self, answer_orig: str) -> float:
        length = len(answer_orig)
        if length > 120 and ("." in answer_orig or "\n" in answer_orig):
            return 4.5
        elif length > 60:
            return 3.5
        return 2.5

    def _score_examples(self, answer_lower: str) -> float:
        example_keywords = {
            "example", "for instance", "such as", "used in", "project",
            "implemented", "code", "model", "dataset", "python", "api", "framework"
        }
        matches = sum(1 for k in example_keywords if k in answer_lower)
        if matches >= 2:
            return 5.0
        elif matches == 1:
            return 3.5
        return 2.0

    def _score_terminology(self, answer_lower: str, topic: str) -> float:
        tech_terms = {
            "agent", "embedding", "vector", "prompt", "llm", "rag", "mcp",
            "transformer", "fine-tuning", "retrieval", "context", "latency",
            "token", "quantization", "api", "database", "pythons", "fastapi", "docker"
        }
        matches = sum(1 for term in tech_terms if term in answer_lower)
        if matches >= 3:
            return 5.0
        elif matches >= 1:
            return 3.5
        return 2.5

    def _score_confidence(self, answer_lower: str) -> float:
        uncertainty = ["i think", "maybe", "probably", "guess", "not sure", "might be"]
        count_unc = sum(1 for u in uncertainty if u in answer_lower)
        if count_unc == 0 and len(answer_lower) > 50:
            return 4.5
        elif count_unc <= 1:
            return 3.5
        return 2.0

    def _determine_follow_up(
        self,
        final_score: float,
        question: PlannedQuestion,
        answer: str,
        dimensions: DimensionalScore,
    ) -> Tuple[bool, Optional[str]]:
        if question.is_follow_up:
            return False, None

        if final_score < LOW_SCORE_THRESHOLD:
            return True, "The response showed gaps in core technical understanding; probing underlying concepts."
        elif dimensions.depth < 2.5:
            return True, "The answer was correct but lacked depth or trade-off analysis."

        return False, None

    def _derive_feedback_notes(
        self,
        dims: DimensionalScore,
        topic: str,
    ) -> Tuple[List[str], List[str]]:
        strengths: List[str] = []
        gaps: List[str] = []

        if dims.correctness >= 4.0:
            strengths.append(f"Demonstrated accurate technical knowledge in {topic}.")
        if dims.depth >= 4.0:
            strengths.append(f"Articulated clear reasoning and architectural trade-offs.")
        if dims.examples >= 4.0:
            strengths.append(f"Supported explanation with relevant real-world examples.")

        if dims.correctness < 3.0:
            gaps.append(f"Gaps identified in core understanding of {topic}.")
        if dims.depth < 3.0:
            gaps.append(f"Explanation of {topic} lacked architectural depth or trade-offs.")
        if dims.examples < 3.0:
            gaps.append(f"Include more practical examples when discussing {topic}.")

        if not strengths:
            strengths.append("Participated actively in technical discussion.")
        if not gaps:
            gaps.append("Continue deepening practical system design experience.")

        return strengths, gaps

    def _clean_answer(self, answer: str) -> str:
        if not isinstance(answer, str):
            return ""
        return " ".join(answer.strip().split())

    def _get_level(self, score: float) -> str:
        if score < 2.0:
            return "weak"
        elif score < 3.0:
            return "developing"
        elif score < 4.0:
            return "good"
        elif score < 4.5:
            return "strong"
        return "excellent"

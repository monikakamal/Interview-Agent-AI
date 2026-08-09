from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from models.schemas import CandidateProfile
from planner import PlannedQuestion


@dataclass
class AnswerEvaluation:
    """
    Evaluation result for one candidate answer.
    """

    question_id: str
    day: int
    topic: str

    score: float
    level: str

    strengths: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)

    needs_follow_up: bool = False
    follow_up_reason: Optional[str] = None

    answered: bool = True
    answer_length: int = 0


@dataclass
class InterviewEvaluation:
    """
    Aggregated evaluation of the complete interview.
    """

    evaluations: List[AnswerEvaluation] = field(default_factory=list)

    @property
    def average_score(self) -> float:
        """
        Return the average score across evaluated answers.
        """

        if not self.evaluations:
            return 0.0

        total = sum(
            evaluation.score
            for evaluation in self.evaluations
        )

        return round(total / len(self.evaluations), 2)

    @property
    def questions_evaluated(self) -> int:
        return len(self.evaluations)

    @property
    def strong_topics(self) -> List[str]:
        """
        Topics where the candidate demonstrated strong understanding.
        """

        topics: List[str] = []

        for evaluation in self.evaluations:
            if evaluation.score >= 4.0:
                if evaluation.topic not in topics:
                    topics.append(evaluation.topic)

        return topics

    @property
    def weak_topics(self) -> List[str]:
        """
        Topics where the candidate showed significant gaps.
        """

        topics: List[str] = []

        for evaluation in self.evaluations:
            if evaluation.score < 3.0:
                if evaluation.topic not in topics:
                    topics.append(evaluation.topic)

        return topics


class AnswerEvaluator:
    """
    Evaluates candidate answers during the interview.

    This evaluator is intentionally deterministic. It does not call
    an external LLM or API.

    The evaluator checks:
        - whether an answer was provided
        - answer length
        - basic technical substance
        - explanation depth
        - engineering reasoning
        - presence of examples/trade-offs
        - whether a follow-up is useful
    """

    MIN_MEANINGFUL_LENGTH = 20
    SHORT_ANSWER_LENGTH = 60
    GOOD_ANSWER_LENGTH = 120
    DETAILED_ANSWER_LENGTH = 250

    FOLLOW_UP_SCORE_THRESHOLD = 3.0

    def __init__(
        self,
        candidate: Optional[CandidateProfile] = None,
    ) -> None:
        self.candidate = candidate

    # ============================================================
    # Public API
    # ============================================================

    def evaluate_answer(
        self,
        question: PlannedQuestion,
        answer: str,
    ) -> AnswerEvaluation:
        """
        Evaluate one candidate answer.

        Args:
            question: The question that was asked.
            answer: Candidate's response.

        Returns:
            AnswerEvaluation containing score, strengths, gaps,
            and follow-up recommendation.
        """

        cleaned_answer = self._clean_answer(answer)

        if not cleaned_answer:
            return AnswerEvaluation(
                question_id=question.question_id,
                day=question.day,
                topic=question.topic,
                score=0.0,
                level="no_answer",
                strengths=[],
                gaps=["No meaningful answer was provided."],
                needs_follow_up=True,
                follow_up_reason="The candidate did not provide an answer.",
                answered=False,
                answer_length=0,
            )

        answer_lower = cleaned_answer.lower()

        score = 0.0
        strengths: List[str] = []
        gaps: List[str] = []

        # --------------------------------------------------------
        # 1. Answer completeness
        # --------------------------------------------------------

        length_score = self._score_length(cleaned_answer)

        score += length_score

        if length_score >= 1.0:
            strengths.append("Provided a substantive response.")
        else:
            gaps.append("The response is too brief to demonstrate depth.")

        # --------------------------------------------------------
        # 2. Explanation / reasoning
        # --------------------------------------------------------

        reasoning_score = self._score_reasoning(answer_lower)

        score += reasoning_score

        if reasoning_score >= 1.0:
            strengths.append(
                "Explained the reasoning behind the answer."
            )
        else:
            gaps.append(
                "The reasoning behind the answer could be explained more clearly."
            )

        # --------------------------------------------------------
        # 3. Technical vocabulary
        # --------------------------------------------------------

        technical_score = self._score_technical_content(
            answer_lower,
            question,
        )

        score += technical_score

        if technical_score >= 1.0:
            strengths.append(
                "Used relevant technical concepts."
            )
        else:
            gaps.append(
                "The answer would benefit from more specific technical details."
            )

        # --------------------------------------------------------
        # 4. Engineering/application thinking
        # --------------------------------------------------------

        engineering_score = self._score_engineering_thinking(
            answer_lower
        )

        score += engineering_score

        if engineering_score >= 1.0:
            strengths.append(
                "Demonstrated practical engineering thinking."
            )
        else:
            gaps.append(
                "Add more implementation or real-world considerations."
            )

        # --------------------------------------------------------
        # 5. Examples / trade-offs / limitations
        # --------------------------------------------------------

        depth_score = self._score_depth(answer_lower)

        score += depth_score

        if depth_score >= 1.0:
            strengths.append(
                "Discussed examples, trade-offs, or limitations."
            )
        else:
            gaps.append(
                "Consider discussing examples, trade-offs, or limitations."
            )

        # --------------------------------------------------------
        # Final score
        # --------------------------------------------------------

        score = round(min(score, 5.0), 2)

        level = self._get_level(score)

        needs_follow_up, follow_up_reason = (
            self._should_follow_up(
                question=question,
                answer=cleaned_answer,
                score=score,
            )
        )

        return AnswerEvaluation(
            question_id=question.question_id,
            day=question.day,
            topic=question.topic,
            score=score,
            level=level,
            strengths=self._unique_items(strengths),
            gaps=self._unique_items(gaps),
            needs_follow_up=needs_follow_up,
            follow_up_reason=follow_up_reason,
            answered=True,
            answer_length=len(cleaned_answer),
        )

    # ============================================================
    # Interview-Level Evaluation
    # ============================================================

    def evaluate_interview(
        self,
        evaluations: List[AnswerEvaluation],
    ) -> InterviewEvaluation:
        """
        Aggregate individual answer evaluations into one
        interview-level evaluation.
        """

        return InterviewEvaluation(
            evaluations=list(evaluations)
        )

    # ============================================================
    # Length Scoring
    # ============================================================

    def _score_length(
        self,
        answer: str,
    ) -> float:
        """
        Score answer completeness.

        Maximum contribution: 1.0
        """

        length = len(answer)

        if length < self.MIN_MEANINGFUL_LENGTH:
            return 0.0

        if length < self.SHORT_ANSWER_LENGTH:
            return 0.5

        if length < self.GOOD_ANSWER_LENGTH:
            return 0.75

        return 1.0

    # ============================================================
    # Reasoning Scoring
    # ============================================================

    def _score_reasoning(
        self,
        answer_lower: str,
    ) -> float:
        """
        Detect basic reasoning/explanation language.

        Maximum contribution: 1.0
        """

        reasoning_terms = {
            "because",
            "therefore",
            "reason",
            "reasoning",
            "why",
            "depends",
            "approach",
            "decision",
            "consider",
            "tradeoff",
            "trade-off",
        }

        matches = sum(
            1
            for term in reasoning_terms
            if term in answer_lower
        )

        if matches >= 3:
            return 1.0

        if matches >= 1:
            return 0.5

        return 0.0

    # ============================================================
    # Technical Content Scoring
    # ============================================================

    def _score_technical_content(
        self,
        answer_lower: str,
        question: PlannedQuestion,
    ) -> float:
        """
        Score use of technical terminology.

        The evaluator uses the curriculum topic as an anchor and
        checks for topic-related terminology.

        Maximum contribution: 1.0
        """

        topic_tokens = self._tokenize(question.topic)

        matches = sum(
            1
            for token in topic_tokens
            if token in answer_lower
        )

        # Generic technical vocabulary helps when the topic title
        # itself is not explicitly repeated in the answer.
        technical_terms = {
            "api",
            "model",
            "data",
            "database",
            "embedding",
            "retrieval",
            "prompt",
            "agent",
            "context",
            "pipeline",
            "architecture",
            "deployment",
            "latency",
            "evaluation",
            "accuracy",
            "security",
            "scaling",
            "vector",
            "llm",
            "rag",
            "mcp",
        }

        technical_matches = sum(
            1
            for term in technical_terms
            if term in answer_lower
        )

        if matches >= 2 or technical_matches >= 4:
            return 1.0

        if matches >= 1 or technical_matches >= 2:
            return 0.5

        return 0.0

    # ============================================================
    # Engineering Thinking
    # ============================================================

    def _score_engineering_thinking(
        self,
        answer_lower: str,
    ) -> float:
        """
        Detect practical implementation thinking.

        Maximum contribution: 1.0
        """

        engineering_terms = {
            "implement",
            "implementation",
            "production",
            "architecture",
            "system",
            "pipeline",
            "deploy",
            "deployment",
            "testing",
            "monitor",
            "monitoring",
            "latency",
            "cost",
            "scalability",
            "scaling",
            "security",
            "error",
            "failure",
            "fallback",
            "logging",
            "cache",
            "validation",
        }

        matches = sum(
            1
            for term in engineering_terms
            if term in answer_lower
        )

        if matches >= 3:
            return 1.0

        if matches >= 1:
            return 0.5

        return 0.0

    # ============================================================
    # Depth Scoring
    # ============================================================

    def _score_depth(
        self,
        answer_lower: str,
    ) -> float:
        """
        Detect examples, alternatives, trade-offs and limitations.

        Maximum contribution: 1.0
        """

        depth_terms = {
            "example",
            "for example",
            "tradeoff",
            "trade-off",
            "limitation",
            "limitations",
            "advantage",
            "disadvantage",
            "alternative",
            "alternatively",
            "risk",
            "problem",
            "challenge",
            "benefit",
            "drawback",
            "pros",
            "cons",
        }

        matches = sum(
            1
            for term in depth_terms
            if term in answer_lower
        )

        if matches >= 2:
            return 1.0

        if matches >= 1:
            return 0.5

        return 0.0

    # ============================================================
    # Follow-up Decision
    # ============================================================

    def _should_follow_up(
        self,
        question: PlannedQuestion,
        answer: str,
        score: float,
    ) -> tuple[bool, Optional[str]]:
        """
        Decide whether the candidate answer deserves a follow-up.

        Follow-ups are especially useful for:
            - very short answers
            - weak answers
            - answers that show partial understanding
            - non-follow-up questions

        A follow-up question is not generated here. This method only
        decides whether one is useful.
        """

        if question.is_follow_up:
            return (
                False,
                None,
            )

        if len(answer) < self.MIN_MEANINGFUL_LENGTH:
            return (
                True,
                "The answer is too short and needs clarification.",
            )

        if score < self.FOLLOW_UP_SCORE_THRESHOLD:
            return (
                True,
                "The answer shows partial understanding and needs deeper probing.",
            )

        # A medium-quality answer can benefit from a deeper question.
        if score < 4.0:
            return (
                True,
                "The candidate demonstrated understanding but could explain the topic in greater depth.",
            )

        return (
            False,
            None,
        )

    # ============================================================
    # Utility Methods
    # ============================================================

    @staticmethod
    def _clean_answer(
        answer: str,
    ) -> str:
        """
        Normalize whitespace and safely handle invalid input.
        """

        if not isinstance(answer, str):
            return ""

        return " ".join(answer.strip().split())

    @staticmethod
    def _tokenize(
        text: str,
    ) -> Set[str]:
        """
        Convert text into simple lowercase tokens.
        """

        if not text:
            return set()

        tokens = set()

        for token in text.lower().replace("-", " ").split():
            cleaned = token.strip(".,!?():;[]{}\"'")

            if cleaned:
                tokens.add(cleaned)

        return tokens

    @staticmethod
    def _get_level(
        score: float,
    ) -> str:
        """
        Convert numeric score to a qualitative level.
        """

        if score <= 0:
            return "no_answer"

        if score < 2.0:
            return "weak"

        if score < 3.0:
            return "developing"

        if score < 4.0:
            return "good"

        if score < 4.5:
            return "strong"

        return "excellent"

    @staticmethod
    def _unique_items(
        items: List[str],
    ) -> List[str]:
        """
        Remove duplicate strings while preserving order.
        """

        seen: Set[str] = set()
        result: List[str] = []

        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)

        return result
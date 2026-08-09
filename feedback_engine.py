from typing import List, Set

from evaluator import AnswerEvaluation, InterviewEvaluation
from models.schemas import CandidateProfile, FeedbackPayload


class FeedbackEngine:
    """
    Generates structured final feedback for a completed interview.

    The engine converts individual answer evaluations into the
    FeedbackPayload required by the API contract.

    This implementation is deterministic and does not require
    an external LLM or API key.
    """

    def __init__(self) -> None:
        pass

    # ============================================================
    # Public API
    # ============================================================

    def generate_feedback(
        self,
        candidate: CandidateProfile,
        evaluations: List[AnswerEvaluation],
    ) -> FeedbackPayload:
        """
        Generate structured feedback for the candidate.

        Args:
            candidate:
                Candidate profile used to personalize the feedback.

            evaluations:
                Individual answer evaluations collected during
                the interview.

        Returns:
            FeedbackPayload compatible with models.schemas.
        """

        interview_evaluation = self._build_interview_evaluation(
            evaluations
        )

        summary = self._generate_summary(
            candidate=candidate,
            evaluation=interview_evaluation,
        )

        strengths = self._generate_strengths(
            evaluation=interview_evaluation
        )

        gaps = self._generate_gaps(
            evaluation=interview_evaluation
        )

        next_steps = self._generate_next_steps(
            evaluation=interview_evaluation
        )

        return FeedbackPayload(
            summary=summary,
            strengths=strengths,
            gaps=gaps,
            next=next_steps,
        )

    # ============================================================
    # Interview Evaluation
    # ============================================================

    @staticmethod
    def _build_interview_evaluation(
        evaluations: List[AnswerEvaluation],
    ) -> InterviewEvaluation:
        """
        Convert the list of individual evaluations into the
        aggregate InterviewEvaluation object.
        """

        return InterviewEvaluation(
            evaluations=list(evaluations)
        )

    # ============================================================
    # Summary
    # ============================================================

    def _generate_summary(
        self,
        candidate: CandidateProfile,
        evaluation: InterviewEvaluation,
    ) -> str:
        """
        Generate an overall interview summary.
        """

        candidate_name = candidate.member.name

        if evaluation.questions_evaluated == 0:
            return (
                f"{candidate_name} did not provide enough responses "
                "to produce a meaningful technical assessment."
            )

        average_score = evaluation.average_score

        level = self._overall_level(
            average_score
        )

        strong_count = len(
            evaluation.strong_topics
        )

        weak_count = len(
            evaluation.weak_topics
        )

        return (
            f"{candidate_name} demonstrated an overall "
            f"{level} level of technical understanding across "
            f"{evaluation.questions_evaluated} evaluated responses. "
            f"The average interview score was "
            f"{average_score:.2f}/5. "
            f"The interview identified {strong_count} strong topic(s) "
            f"and {weak_count} topic(s) that would benefit from "
            "further development."
        )

    # ============================================================
    # Strengths
    # ============================================================

    def _generate_strengths(
        self,
        evaluation: InterviewEvaluation,
    ) -> List[str]:
        """
        Generate a concise list of candidate strengths.
        """

        strengths: List[str] = []

        # --------------------------------------------------------
        # Topic-level strengths
        # --------------------------------------------------------

        for topic in evaluation.strong_topics:
            strengths.append(
                f"Strong understanding demonstrated in {topic}."
            )

        # --------------------------------------------------------
        # Evaluation-level strengths
        # --------------------------------------------------------

        for answer_evaluation in evaluation.evaluations:

            for strength in answer_evaluation.strengths:

                if strength not in strengths:
                    strengths.append(strength)

        # --------------------------------------------------------
        # Fallback
        # --------------------------------------------------------

        if not strengths:
            strengths.append(
                "The candidate participated in the interview "
                "and provided responses that can be used for "
                "further technical development."
            )

        return self._limit_items(
            strengths,
            limit=6,
        )

    # ============================================================
    # Gaps
    # ============================================================

    def _generate_gaps(
        self,
        evaluation: InterviewEvaluation,
    ) -> List[str]:
        """
        Generate a concise list of areas requiring improvement.
        """

        gaps: List[str] = []

        # --------------------------------------------------------
        # Topic-level gaps
        # --------------------------------------------------------

        for topic in evaluation.weak_topics:
            gaps.append(
                f"Further depth is needed in {topic}."
            )

        # --------------------------------------------------------
        # Evaluation-level gaps
        # --------------------------------------------------------

        for answer_evaluation in evaluation.evaluations:

            for gap in answer_evaluation.gaps:

                if gap not in gaps:
                    gaps.append(gap)

        # --------------------------------------------------------
        # Fallback
        # --------------------------------------------------------

        if not gaps:
            gaps.append(
                "No major recurring technical gaps were identified "
                "from the evaluated responses."
            )

        return self._limit_items(
            gaps,
            limit=6,
        )

    # ============================================================
    # Next Steps
    # ============================================================

    def _generate_next_steps(
        self,
        evaluation: InterviewEvaluation,
    ) -> List[str]:
        """
        Generate actionable next steps from identified gaps.
        """

        next_steps: List[str] = []

        weak_topics = evaluation.weak_topics

        for topic in weak_topics:
            next_steps.append(
                f"Review {topic} and practice explaining its "
                "architecture, implementation decisions, and "
                "real-world trade-offs."
            )

        # --------------------------------------------------------
        # Score-based recommendations
        # --------------------------------------------------------

        average_score = evaluation.average_score

        if average_score < 3.0:
            next_steps.append(
                "Strengthen core concepts before moving to more "
                "advanced system-design questions."
            )

        elif average_score < 4.0:
            next_steps.append(
                "Practice deeper technical explanations and "
                "connect concepts to concrete implementation examples."
            )

        else:
            next_steps.append(
                "Continue practicing production-oriented system "
                "design and trade-off discussions."
            )

        # --------------------------------------------------------
        # Follow-up related recommendation
        # --------------------------------------------------------

        follow_up_count = sum(
            1
            for item in evaluation.evaluations
            if item.needs_follow_up
        )

        if follow_up_count > 0:
            next_steps.append(
                "Practice giving complete answers that explain "
                "the reasoning, implementation choices, and "
                "trade-offs without requiring repeated probing."
            )

        # --------------------------------------------------------
        # Ensure actionable feedback
        # --------------------------------------------------------

        if not next_steps:
            next_steps.append(
                "Continue practicing technical interview questions "
                "using real project examples."
            )

        return self._limit_items(
            next_steps,
            limit=6,
        )

    # ============================================================
    # Overall Level
    # ============================================================

    @staticmethod
    def _overall_level(
        score: float,
    ) -> str:
        """
        Convert average score into an overall qualitative level.
        """

        if score <= 0:
            return "insufficient"

        if score < 2.0:
            return "weak"

        if score < 3.0:
            return "developing"

        if score < 4.0:
            return "good"

        if score < 4.5:
            return "strong"

        return "excellent"

    # ============================================================
    # Utility Methods
    # ============================================================

    @staticmethod
    def _limit_items(
        items: List[str],
        limit: int,
    ) -> List[str]:
        """
        Remove duplicates and limit the number of feedback items.
        """

        unique_items: List[str] = []
        seen: Set[str] = set()

        for item in items:
            cleaned = item.strip()

            if not cleaned:
                continue

            if cleaned in seen:
                continue

            seen.add(cleaned)
            unique_items.append(cleaned)

            if len(unique_items) >= limit:
                break

        return unique_items
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from models.schemas import CandidateProfile, CurriculumDay
from retriever import DataRetriever


@dataclass
class PlannedQuestion:
    """
    Represents one question planned for the interview.
    """

    question_id: str
    day: int
    topic: str
    question_type: str
    prompt: str
    is_follow_up: bool = False
    parent_question_id: Optional[str] = None


@dataclass
class InterviewPlan:
    """
    Complete deterministic interview plan.

    The plan guarantees:
        - minimum 8 questions
        - minimum 4 curriculum days
        whenever at least 4 relevant curriculum days are available.
    """

    questions: List[PlannedQuestion] = field(default_factory=list)
    curriculum_days: List[int] = field(default_factory=list)

    @property
    def question_count(self) -> int:
        return len(self.questions)

    @property
    def curriculum_day_count(self) -> int:
        return len(set(self.curriculum_days))

    @property
    def is_minimum_requirement_met(self) -> bool:
        return (
            self.question_count >= 8
            and self.curriculum_day_count >= 4
        )


class InterviewPlanner:
    """
    Creates an interview plan from the candidate's learning journey
    and the curriculum.

    This class does NOT evaluate answers and does NOT maintain
    persistent session state.
    """

    MIN_QUESTIONS = 8
    MIN_CURRICULUM_DAYS = 4

    def __init__(
        self,
        retriever: DataRetriever,
    ) -> None:
        self.retriever = retriever

    # ============================================================
    # Public API
    # ============================================================

    def create_plan(
        self,
        candidate: CandidateProfile,
        covered_days: Optional[List[int]] = None,
        asked_question_ids: Optional[List[str]] = None,
    ) -> InterviewPlan:
        """
        Create a personalized interview plan.

        Priority:
            1. Completed curriculum days
            2. Attempted but incomplete curriculum days
            3. Other available curriculum days as fallback

        Already covered days and already planned question IDs
        are excluded where possible.
        """

        covered: Set[int] = set(covered_days or [])
        asked_ids: Set[str] = set(asked_question_ids or [])

        curriculum_days = self._select_curriculum_days(
            candidate=candidate,
            covered_days=covered,
        )

        questions = self._build_questions(
            curriculum_days=curriculum_days,
            asked_question_ids=asked_ids,
        )

        # If the candidate has fewer than four eligible learning days,
        # use additional curriculum days as a fallback.
        if len({q.day for q in questions}) < self.MIN_CURRICULUM_DAYS:
            questions = self._add_fallback_days(
                questions=questions,
                candidate=candidate,
                covered_days=covered,
                asked_question_ids=asked_ids,
            )

        # Guarantee at least 8 planned questions when enough curriculum
        # content is available.
        questions = self._ensure_minimum_questions(
            questions=questions,
            curriculum_days=curriculum_days,
            asked_question_ids=asked_ids,
        )

        curriculum_day_numbers = sorted(
            {question.day for question in questions}
        )

        return InterviewPlan(
            questions=questions,
            curriculum_days=curriculum_day_numbers,
        )

    # ============================================================
    # Curriculum Selection
    # ============================================================

    def _select_curriculum_days(
        self,
        candidate: CandidateProfile,
        covered_days: Set[int],
    ) -> List[CurriculumDay]:
        """
        Select curriculum days relevant to the candidate.

        Completed days are preferred over merely attempted days.
        Skipped days are not selected as completed learning.
        """

        relevant_days = self.retriever.get_relevant_curriculum(
            candidate=candidate,
            exclude_days=list(covered_days),
        )

        return relevant_days

    # ============================================================
    # Question Construction
    # ============================================================

    def _build_questions(
        self,
        curriculum_days: List[CurriculumDay],
        asked_question_ids: Set[str],
    ) -> List[PlannedQuestion]:
        """
        Build a base set of questions.

        Each selected curriculum day initially receives two questions:
            - one conceptual question
            - one engineering/application question
        """

        questions: List[PlannedQuestion] = []

        for curriculum_day in curriculum_days:
            day_questions = self._questions_for_day(curriculum_day)

            for question in day_questions:
                if question.question_id in asked_question_ids:
                    continue

                questions.append(question)

                if len(questions) >= self.MIN_QUESTIONS:
                    return questions

        return questions

    def _questions_for_day(
        self,
        curriculum_day: CurriculumDay,
    ) -> List[PlannedQuestion]:
        """
        Create deterministic question templates for one curriculum day.

        The actual conversational wording can later be refined by the
        interview agent/LLM.
        """

        day = curriculum_day.day
        title = curriculum_day.title

        objective = (
            curriculum_day.objectives[0]
            if curriculum_day.objectives
            else title
        )

        tool = (
            curriculum_day.tools[0]
            if curriculum_day.tools
            else "the relevant tools"
        )

        return [
            PlannedQuestion(
                question_id=f"day-{day}-q1",
                day=day,
                topic=title,
                question_type="conceptual",
                prompt=(
                    f"Explain {title} in your own words. "
                    f"What did you learn from this part of the cohort?"
                ),
            ),
            PlannedQuestion(
                question_id=f"day-{day}-q2",
                day=day,
                topic=title,
                question_type="engineering",
                prompt=(
                    f"Suppose you were implementing {title} in a "
                    f"real AI system. How would you approach it, "
                    f"and what engineering decisions would you make?"
                ),
            ),
            PlannedQuestion(
                question_id=f"day-{day}-q3",
                day=day,
                topic=title,
                question_type="application",
                prompt=(
                    f"How would you apply what you learned in "
                    f"{title} to a practical project? "
                    f"Consider the objective: {objective}"
                ),
            ),
            PlannedQuestion(
                question_id=f"day-{day}-q4",
                day=day,
                topic=title,
                question_type="tools",
                prompt=(
                    f"What role does {tool} play in this topic, "
                    f"and what would you consider when choosing "
                    f"or using it?"
                ),
            ),
        ]

    # ============================================================
    # Fallback Curriculum
    # ============================================================

    def _add_fallback_days(
        self,
        questions: List[PlannedQuestion],
        candidate: CandidateProfile,
        covered_days: Set[int],
        asked_question_ids: Set[str],
    ) -> List[PlannedQuestion]:
        """
        Add additional curriculum days when the candidate's
        completed/attempted learning history does not provide
        four distinct days.

        This is necessary because the challenge requires coverage
        across at least four curriculum days.
        """

        current_days = {question.day for question in questions}

        curriculum = self.retriever.load_curriculum()

        for curriculum_day in curriculum.days:
            if len(current_days) >= self.MIN_CURRICULUM_DAYS:
                break

            if curriculum_day.day in covered_days:
                continue

            if curriculum_day.day in current_days:
                continue

            day_questions = self._questions_for_day(curriculum_day)

            for question in day_questions:
                if question.question_id in asked_question_ids:
                    continue

                questions.append(question)
                current_days.add(curriculum_day.day)
                break

        return questions

    # ============================================================
    # Minimum Question Guarantee
    # ============================================================

    def _ensure_minimum_questions(
        self,
        questions: List[PlannedQuestion],
        curriculum_days: List[CurriculumDay],
        asked_question_ids: Set[str],
    ) -> List[PlannedQuestion]:
        """
        Ensure the plan contains at least eight unique questions
        whenever enough curriculum content is available.
        """

        if len(questions) >= self.MIN_QUESTIONS:
            return questions

        existing_ids = {
            question.question_id
            for question in questions
        }

        existing_ids.update(asked_question_ids)

        for curriculum_day in curriculum_days:
            day_questions = self._questions_for_day(curriculum_day)

            for question in day_questions:
                if question.question_id in existing_ids:
                    continue

                questions.append(question)
                existing_ids.add(question.question_id)

                if len(questions) >= self.MIN_QUESTIONS:
                    return questions

        return questions

    # ============================================================
    # Follow-up Planning
    # ============================================================

    def create_follow_up(
        self,
        parent_question: PlannedQuestion,
        candidate_answer: str,
    ) -> Optional[PlannedQuestion]:
        """
        Create a follow-up question based on the candidate's answer.

        The planner creates the follow-up structure; evaluator.py
        determines whether the answer actually needs a follow-up.

        Returns None when the answer is empty.
        """

        if not candidate_answer or not candidate_answer.strip():
            return None

        question_id = f"{parent_question.question_id}-followup"

        return PlannedQuestion(
            question_id=question_id,
            day=parent_question.day,
            topic=parent_question.topic,
            question_type="follow_up",
            prompt=(
                f"You mentioned that {self._summarize_answer(candidate_answer)}. "
                f"Can you explain why you made that choice and what "
                f"trade-offs or limitations you would consider?"
            ),
            is_follow_up=True,
            parent_question_id=parent_question.question_id,
        )

    # ============================================================
    # Interview Progress
    # ============================================================

    @staticmethod
    def get_covered_days(
        questions: List[PlannedQuestion],
    ) -> List[int]:
        """
        Return curriculum days covered by the supplied questions.
        """

        return sorted(
            {
                question.day
                for question in questions
            }
        )

    @staticmethod
    def get_remaining_questions(
        plan: InterviewPlan,
        asked_question_ids: List[str],
    ) -> List[PlannedQuestion]:
        """
        Return questions from the plan that have not yet been asked.
        """

        asked: Set[str] = set(asked_question_ids)

        return [
            question
            for question in plan.questions
            if question.question_id not in asked
        ]

    # ============================================================
    # Internal Text Helper
    # ============================================================

    @staticmethod
    def _summarize_answer(
        answer: str,
        max_length: int = 180,
    ) -> str:
        """
        Create a short safe excerpt for a follow-up prompt.

        This is intentionally simple. The evaluator/LLM can later
        produce a richer interpretation of the answer.
        """

        cleaned = " ".join(answer.split())

        if len(cleaned) <= max_length:
            return cleaned

        return cleaned[:max_length].rstrip() + "..."
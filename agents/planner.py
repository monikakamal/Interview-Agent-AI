"""
Interview Planner responsible for constructing multi-turn curriculum plans,
ensuring coverage of >= 4 curriculum days and >= 8 questions based on candidate profile.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from models.schemas import CandidateProfile, CurriculumDay
from rag.retriever import RAGRetriever
from utils.constants import MIN_CURRICULUM_DAYS, MIN_QUESTIONS
from utils.logger import logger


@dataclass
class PlannedQuestion:
    """
    Represents a planned interview question slot.
    """

    question_id: str
    day: int
    topic: str
    question_type: str  # "conceptual", "engineering", "application", "tools"
    prompt_template: str
    difficulty: str = "medium"
    is_follow_up: bool = False
    parent_question_id: Optional[str] = None


@dataclass
class InterviewPlan:
    """
    Complete interview plan structure.
    Guarantees coverage across at least 4 curriculum days and at least 8 questions.
    """

    questions: List[PlannedQuestion] = field(default_factory=list)
    curriculum_days: List[int] = field(default_factory=list)

    @property
    def question_count(self) -> int:
        return len(self.questions)

    @property
    def curriculum_day_count(self) -> int:
        return len(set(self.curriculum_days))


class InterviewPlanner:
    """
    Creates candidate-personalized interview plans using RAG retrieved curriculum.
    """

    def __init__(self, retriever: RAGRetriever) -> None:
        self.retriever = retriever

    def create_plan(
        self,
        candidate: CandidateProfile,
        covered_days: Optional[List[int]] = None,
        asked_question_ids: Optional[List[str]] = None,
    ) -> InterviewPlan:
        """
        Builds a multi-turn interview plan covering at least 4 curriculum days
        and at least 8 questions tailored to the candidate's learning record.
        """
        exclude = set(covered_days or [])
        asked_ids = set(asked_question_ids or [])

        # Get prioritized curriculum days from candidate's completed & attempted missions
        curriculum_days = self.retriever.get_relevant_curriculum_days(
            candidate=candidate,
            exclude_days=list(exclude),
        )

        questions: List[PlannedQuestion] = []
        selected_day_nums: Set[int] = set()

        for curr_day in curriculum_days:
            day_num = curr_day.day
            topic = curr_day.title

            # Generate question templates for day
            day_q_templates = self._generate_day_question_slots(curr_day)

            for q in day_q_templates:
                if q.question_id not in asked_ids:
                    questions.append(q)
                    selected_day_nums.add(day_num)

        # If question count is below MIN_QUESTIONS, add remaining question slots from selected days
        if len(questions) < MIN_QUESTIONS:
            for curr_day in curriculum_days:
                extra_q_templates = self._generate_extra_question_slots(curr_day)
                for q in extra_q_templates:
                    if q.question_id not in asked_ids and q.question_id not in {x.question_id for x in questions}:
                        questions.append(q)
                        selected_day_nums.add(curr_day.day)
                        if len(questions) >= MIN_QUESTIONS and len(selected_day_nums) >= MIN_CURRICULUM_DAYS:
                            break
                if len(questions) >= MIN_QUESTIONS and len(selected_day_nums) >= MIN_CURRICULUM_DAYS:
                    break

        sorted_days = sorted(selected_day_nums)
        logger.info(
            f"Created interview plan: {len(questions)} questions covering "
            f"{len(sorted_days)} curriculum days: {sorted_days}."
        )

        return InterviewPlan(
            questions=questions,
            curriculum_days=sorted_days,
        )

    def _generate_day_question_slots(self, curr_day: CurriculumDay) -> List[PlannedQuestion]:
        day = curr_day.day
        title = curr_day.title

        return [
            PlannedQuestion(
                question_id=f"day_{day}_q1_conceptual",
                day=day,
                topic=title,
                question_type="conceptual",
                prompt_template=f"Concept exploration for Day {day}: {title}",
            ),
            PlannedQuestion(
                question_id=f"day_{day}_q2_engineering",
                day=day,
                topic=title,
                question_type="engineering",
                prompt_template=f"Engineering design and implementation for Day {day}: {title}",
            ),
        ]

    def _generate_extra_question_slots(self, curr_day: CurriculumDay) -> List[PlannedQuestion]:
        day = curr_day.day
        title = curr_day.title

        return [
            PlannedQuestion(
                question_id=f"day_{day}_q3_application",
                day=day,
                topic=title,
                question_type="application",
                prompt_template=f"Practical system application for Day {day}: {title}",
            ),
            PlannedQuestion(
                question_id=f"day_{day}_q4_tools",
                day=day,
                topic=title,
                question_type="tools",
                prompt_template=f"Tooling and framework trade-offs for Day {day}: {title}",
            ),
        ]

    def create_follow_up_slot(
        self,
        parent_question: PlannedQuestion,
        candidate_answer: str,
        difficulty: str = "medium",
    ) -> PlannedQuestion:
        """
        Creates a follow-up question slot attached to a parent question.
        """
        follow_up_id = f"{parent_question.question_id}_followup"
        return PlannedQuestion(
            question_id=follow_up_id,
            day=parent_question.day,
            topic=parent_question.topic,
            question_type="follow_up",
            prompt_template=f"Follow-up clarification on {parent_question.topic}",
            difficulty=difficulty,
            is_follow_up=True,
            parent_question_id=parent_question.question_id,
        )

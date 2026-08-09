"""
Session memory management for tracking interview state, question history, turn scores,
covered concepts, weak concepts, and adaptive difficulty levels.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
import threading

from models.schemas import CandidateProfile, FeedbackPayload
from utils.constants import DIFFICULTY_MEDIUM


@dataclass
class TurnRecord:
    """
    Record of a single question-answer exchange turn in the interview.
    """

    question_id: str
    day: int
    topic: str
    question_text: str
    answer_text: Optional[str] = None
    score: Optional[float] = None
    level: Optional[str] = None
    strengths: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    is_follow_up: bool = False
    parent_question_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class SessionMemory:
    """
    Stores and manages full memory state for an active interview session.
    """

    def __init__(self, session_id: str, candidate: CandidateProfile) -> None:
        self.session_id = session_id
        self.candidate = candidate
        self.turns: List[TurnRecord] = []
        self.asked_question_ids: Set[str] = set()
        self.covered_days: Set[int] = set()
        self.covered_concepts: List[str] = []
        self.weak_concepts: List[str] = []
        self.current_difficulty: str = DIFFICULTY_MEDIUM
        self.done: bool = False
        self.feedback: Optional[FeedbackPayload] = None
        self.current_turn_index: int = 0
        self.plan_questions: List = []

    def record_asked_question(
        self,
        question_id: str,
        day: int,
        topic: str,
        question_text: str,
        is_follow_up: bool = False,
        parent_question_id: Optional[str] = None,
    ) -> TurnRecord:
        """
        Record a question asked to the candidate.
        """
        self.asked_question_ids.add(question_id)
        self.covered_days.add(day)

        turn = TurnRecord(
            question_id=question_id,
            day=day,
            topic=topic,
            question_text=question_text,
            is_follow_up=is_follow_up,
            parent_question_id=parent_question_id,
        )
        self.turns.append(turn)
        return turn

    def get_latest_turn(self) -> Optional[TurnRecord]:
        return self.turns[-1] if self.turns else None

    def update_latest_answer_and_eval(
        self,
        answer_text: str,
        score: float,
        level: str,
        strengths: List[str],
        gaps: List[str],
    ) -> None:
        """
        Update the latest turn with candidate's answer and evaluation.
        """
        if not self.turns:
            return

        latest = self.turns[-1]
        latest.answer_text = answer_text
        latest.score = score
        latest.level = level
        latest.strengths = strengths
        latest.gaps = gaps

        # Update concepts covered & weak concepts
        if latest.topic not in self.covered_concepts:
            self.covered_concepts.append(latest.topic)

        if score < 3.0:
            if latest.topic not in self.weak_concepts:
                self.weak_concepts.append(latest.topic)

    def set_difficulty(self, new_difficulty: str) -> None:
        self.current_difficulty = new_difficulty

    def get_conversation_history_context(self) -> str:
        """
        Builds a conversational summary string of previous turns for LLM prompt context.
        """
        history_lines = []
        for idx, turn in enumerate(self.turns, 1):
            history_lines.append(f"Turn {idx} [Day {turn.day} - {turn.topic}]")
            history_lines.append(f"Interviewer: {turn.question_text}")
            if turn.answer_text:
                history_lines.append(f"Candidate: {turn.answer_text}")
                if turn.score is not None:
                    history_lines.append(f"Evaluation Score: {turn.score:.1f}/5.0 ({turn.level})")
            history_lines.append("")
        return "\n".join(history_lines)

    @property
    def answered_count(self) -> int:
        return sum(1 for t in self.turns if t.answer_text is not None)

    @property
    def average_score(self) -> float:
        scored = [t.score for t in self.turns if t.score is not None]
        if not scored:
            return 0.0
        return round(sum(scored) / len(scored), 2)


class SessionMemoryStore:
    """
    Thread-safe in-memory store for active session memories.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionMemory] = {}
        self._lock = threading.Lock()

    def get_session(self, session_id: str) -> Optional[SessionMemory]:
        with self._lock:
            return self._sessions.get(session_id)

    def create_session(self, session_id: str, candidate: CandidateProfile) -> SessionMemory:
        with self._lock:
            session = SessionMemory(session_id=session_id, candidate=candidate)
            self._sessions[session_id] = session
            return session

    def remove_session(self, session_id: str) -> None:
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]

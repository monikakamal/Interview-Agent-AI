"""
Interview Service orchestrating SessionMemory, RAGRetriever, InterviewPlanner,
InterviewerAgent, AnswerEvaluator, and FeedbackEngine into a unified interview flow.
"""

import traceback
from typing import Optional, Tuple
from fastapi import HTTPException

from agents.evaluator import AnswerEvaluator
from agents.feedback import FeedbackEngine
from agents.interviewer import InterviewerAgent
from agents.planner import InterviewPlan, InterviewPlanner, PlannedQuestion
from memory.session_memory import SessionMemory, SessionMemoryStore
from models.schemas import CandidateProfile, FeedbackPayload, InterviewRequest, InterviewResponse
from rag.retriever import RAGRetriever
from utils.constants import DIFFICULTY_EASY, DIFFICULTY_HARD, DIFFICULTY_MEDIUM, MIN_CURRICULUM_DAYS, MIN_QUESTIONS
from utils.logger import logger


class InterviewService:
    """
    Core orchestration service for managing AI technical interview lifecycles.
    """

    def __init__(
        self,
        retriever: RAGRetriever,
        session_store: Optional[SessionMemoryStore] = None,
    ) -> None:
        logger.info("-> Entering InterviewService.__init__()")
        self.retriever = retriever
        self.session_store = session_store or SessionMemoryStore()
        self.planner = InterviewPlanner(retriever=self.retriever)
        self.interviewer = InterviewerAgent()
        self.evaluator = AnswerEvaluator()
        self.feedback_engine = FeedbackEngine()
        logger.info("Retriever initialized and InterviewService ready.")

    def process_interview_request(self, request: InterviewRequest) -> InterviewResponse:
        """
        Main entrypoint processing POST /api/interview requests.
        Handles session initialization, conversation turns, and final completion.
        """
        logger.info("-> Entering process_interview_request()")
        session_id = (request.sessionId or "").strip()
        if not session_id:
            logger.warning("Validation failure: sessionId must not be empty.")
            raise HTTPException(status_code=400, detail="sessionId must not be empty.")

        session = self.session_store.get_session(session_id)

        # ----------------------------------------------------
        # Turn 1: Start New Interview Session
        # ----------------------------------------------------
        if session is None:
            logger.info(f"Session '{session_id}' not found in store; initializing new interview session.")
            return self._start_new_session(session_id, request)

        logger.info(f"Session '{session_id}' found in memory store.")

        # ----------------------------------------------------
        # Subsequent Turns: Existing Session
        # ----------------------------------------------------
        if session.done:
            logger.warning(f"Session '{session_id}' is already marked done.")
            raise HTTPException(
                status_code=409,
                detail="This interview session has already completed.",
            )

        message = (request.message or "").strip()
        if not message:
            logger.warning(f"Validation failure: message required for existing session '{session_id}'.")
            raise HTTPException(
                status_code=400,
                detail="message is required for an existing interview session.",
            )

        return self._process_conversation_turn(session, message)

    def _start_new_session(self, session_id: str, request: InterviewRequest) -> InterviewResponse:
        logger.info(f"-> Entering _start_new_session() for session_id='{session_id}'")
        candidate: Optional[CandidateProfile] = None

        # 1. Parse Candidate Profile dict if provided
        if request.candidate:
            try:
                candidate = CandidateProfile(**request.candidate)
                logger.info(f"Candidate parsed successfully from payload: name='{candidate.member.name}'")
            except Exception as exc:
                logger.warning(f"Candidate object parsing failed: {exc}. Full traceback:\n{traceback.format_exc()}")
                logger.info("Attempting fallback candidate resolution from dataset.")

        # 2. Lookup Candidate via candidateId if candidate object not set
        if candidate is None and request.candidateId:
            try:
                candidate = self.retriever.get_candidate(request.candidateId)
                if candidate:
                    logger.info(f"Candidate fetched via ID '{request.candidateId}': name='{candidate.member.name}'")
                else:
                    logger.warning(f"Candidate lookup failed: Candidate with ID '{request.candidateId}' not found in candidates.json.")
            except Exception as exc:
                logger.error(f"Error during candidate lookup for ID '{request.candidateId}': {exc}\n{traceback.format_exc()}")

        # 3. Fallback Candidate Resolution (Never return 404 for new session)
        if candidate is None:
            logger.info("Automatically resolving default candidate profile from dataset to create new interview session.")
            candidate = self._get_fallback_candidate()
            if candidate is None:
                logger.error("Critical: Default candidate dataset empty or missing.")
                raise HTTPException(
                    status_code=500,
                    detail="Curriculum candidate data is unavailable.",
                )
            logger.info(f"Created session using default candidate: name='{candidate.member.name}'")

        # 4. Create Session in Memory Store
        session = self.session_store.create_session(session_id, candidate)
        logger.info(f"Session created in memory store for session_id='{session_id}'")

        # 5. Generate Interview Plan
        try:
            plan = self.planner.create_plan(candidate=candidate)
            session.plan_questions = plan.questions
            logger.info(f"Curriculum plan generated: {len(plan.questions)} questions across {len(plan.curriculum_days)} days.")
        except Exception as exc:
            logger.error(f"Interview planning failed: {exc}\n{traceback.format_exc()}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to generate curriculum interview plan: {exc}",
            )

        if not session.plan_questions:
            logger.error("Generated interview plan contains 0 questions.")
            raise HTTPException(
                status_code=422,
                detail="Unable to generate curriculum interview plan for candidate.",
            )

        # 6. Retrieve RAG Context & Generate First Question
        first_q: PlannedQuestion = session.plan_questions[0]
        rag_context = self.retriever.get_context_for_day(first_q.day)
        logger.info(f"Retrieved RAG context for Day {first_q.day} ({first_q.topic}): len={len(rag_context)}")

        first_prompt = self.interviewer.generate_question(
            session=session,
            planned_question=first_q,
            rag_context=rag_context,
        )
        logger.info(f"First question generated: '{first_prompt[:80]}...'")

        session.record_asked_question(
            question_id=first_q.question_id,
            day=first_q.day,
            topic=first_q.topic,
            question_text=first_prompt,
        )

        welcome_reply = (
            f"Welcome to your technical interview, {candidate.member.name}. Let's begin.\n\n"
            f"{first_prompt}"
        )

        logger.info("-> Exiting _start_new_session() successfully with InterviewResponse")
        return InterviewResponse(
            reply=welcome_reply,
            done=False,
            feedback=None,
        )

    def _process_conversation_turn(self, session: SessionMemory, candidate_message: str) -> InterviewResponse:
        logger.info(f"-> Entering _process_conversation_turn() for session_id='{session.session_id}', turn_idx={session.current_turn_index}")
        latest_turn = session.get_latest_turn()
        if latest_turn is None:
            logger.error("Inconsistent session state: latest turn is None.")
            raise HTTPException(status_code=500, detail="Inconsistent interview session state.")

        current_q = session.plan_questions[session.current_turn_index]
        rag_context = self.retriever.get_context_for_day(current_q.day)

        # 1. Evaluate candidate answer
        logger.info(f"Evaluating candidate answer for topic '{current_q.topic}'")
        evaluation = self.evaluator.evaluate_answer(
            question=current_q,
            answer=candidate_message,
            rag_context=rag_context,
        )
        logger.info(f"Answer evaluation complete: score={evaluation.score:.2f}/5.0, level='{evaluation.level}'")

        # 2. Update session memory with turn evaluation & scores
        session.update_latest_answer_and_eval(
            answer_text=candidate_message,
            score=evaluation.score,
            level=evaluation.level,
            strengths=evaluation.strengths,
            gaps=evaluation.gaps,
        )

        # 3. Adaptive Difficulty adjustment
        if evaluation.score >= 4.0:
            session.set_difficulty(DIFFICULTY_HARD)
        elif evaluation.score < 2.5:
            session.set_difficulty(DIFFICULTY_EASY)
        else:
            session.set_difficulty(DIFFICULTY_MEDIUM)

        # 4. Handle follow-up question if needed
        if evaluation.needs_follow_up and not current_q.is_follow_up:
            logger.info("Follow-up required based on answer score/depth.")
            follow_up_prompt = self.interviewer.generate_follow_up(
                session=session,
                parent_question=current_q,
                candidate_answer=candidate_message,
                score=evaluation.score,
                rag_context=rag_context,
            )

            follow_up_q = self.planner.create_follow_up_slot(
                parent_question=current_q,
                candidate_answer=candidate_message,
                difficulty=session.current_difficulty,
            )

            session.plan_questions.insert(session.current_turn_index + 1, follow_up_q)
            session.current_turn_index += 1

            session.record_asked_question(
                question_id=follow_up_q.question_id,
                day=follow_up_q.day,
                topic=follow_up_q.topic,
                question_text=follow_up_prompt,
                is_follow_up=True,
                parent_question_id=current_q.question_id,
            )

            logger.info("Returning follow-up InterviewResponse")
            return InterviewResponse(
                reply=follow_up_prompt,
                done=False,
                feedback=None,
            )

        # Move to next question slot
        session.current_turn_index += 1

        # 5. Check if interview completion criteria are satisfied
        if self._is_interview_complete(session):
            logger.info(f"Interview completed for session '{session.session_id}'. Generating final feedback.")
            session.done = True
            feedback = self.feedback_engine.generate_feedback(session)
            session.feedback = feedback

            logger.info("Returning final completion InterviewResponse with feedback payload.")
            return InterviewResponse(
                reply="Interview completed. Thank you for your responses!",
                done=True,
                feedback=feedback,
            )

        # 6. Ask Next Question from Plan
        next_q: PlannedQuestion = session.plan_questions[session.current_turn_index]
        next_rag_context = self.retriever.get_context_for_day(next_q.day)

        next_prompt = self.interviewer.generate_question(
            session=session,
            planned_question=next_q,
            rag_context=next_rag_context,
        )

        session.record_asked_question(
            question_id=next_q.question_id,
            day=next_q.day,
            topic=next_q.topic,
            question_text=next_prompt,
        )

        logger.info("Returning next question InterviewResponse")
        return InterviewResponse(
            reply=next_prompt,
            done=False,
            feedback=None,
        )

    def _is_interview_complete(self, session: SessionMemory) -> bool:
        """
        Checks if minimum question count (>=8) and curriculum days (>=4) are met
        and all plan questions have been exhausted.
        """
        questions_answered = session.answered_count
        days_covered_count = len(session.covered_days)

        min_satisfied = (
            questions_answered >= MIN_QUESTIONS and
            days_covered_count >= MIN_CURRICULUM_DAYS
        )

        no_remaining_questions = session.current_turn_index >= len(session.plan_questions)

        return min_satisfied or no_remaining_questions

    def _get_fallback_candidate(self) -> Optional[CandidateProfile]:
        """
        Safely retrieves the first available candidate profile from dataset as a fallback.
        """
        try:
            candidates_data = self.retriever.loader.load_candidates()
            if candidates_data.candidates:
                return candidates_data.candidates[0]
        except Exception as exc:
            logger.error(f"Fallback candidate lookup failed: {exc}\n{traceback.format_exc()}")
        return None

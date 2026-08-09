from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from evaluator import (
    AnswerEvaluation,
    AnswerEvaluator,
)
from feedback_engine import FeedbackEngine
from models.schemas import (
    CandidateProfile,
    FeedbackPayload,
    InterviewRequest,
    InterviewResponse,
)
from planner import (
    InterviewPlan,
    InterviewPlanner,
    PlannedQuestion,
)
from retriever import DataRetriever


# ============================================================
# FastAPI Application
# ============================================================

app = FastAPI(
    title="AI Interview Agent",
    description=(
        "Personalized multi-turn technical interview agent "
        "for the AI Cohort."
    ),
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Dependencies
# ============================================================

retriever = DataRetriever()
planner = InterviewPlanner(retriever=retriever)
feedback_engine = FeedbackEngine()


# ============================================================
# In-Memory Interview Session
# ============================================================

@dataclass
class InterviewSession:
    """
    Stores the state of one active interview session.

    Long-term persistence is intentionally not implemented because
    persistent user accounts and long-term conversation history are
    outside the challenge requirements.
    """

    session_id: str
    candidate: CandidateProfile

    plan: InterviewPlan

    current_question_index: int = 0

    asked_question_ids: List[str] = field(default_factory=list)

    evaluations: List[AnswerEvaluation] = field(
        default_factory=list
    )

    conversation: List[Dict[str, str]] = field(
        default_factory=list
    )

    covered_days: List[int] = field(
        default_factory=list
    )

    done: bool = False


# Active sessions for the running application.

SESSIONS: Dict[str, InterviewSession] = {}


# ============================================================
# Helper Functions
# ============================================================

def _get_current_question(
    session: InterviewSession,
) -> Optional[PlannedQuestion]:
    """
    Return the current unanswered planned question.
    """

    while (
        session.current_question_index
        < len(session.plan.questions)
    ):
        question = session.plan.questions[
            session.current_question_index
        ]

        if question.question_id not in session.asked_question_ids:
            return question

        session.current_question_index += 1

    return None


def _record_question(
    session: InterviewSession,
    question: PlannedQuestion,
) -> None:
    """
    Mark a question as asked and update the session context.
    """

    if question.question_id not in session.asked_question_ids:
        session.asked_question_ids.append(
            question.question_id
        )

    if question.day not in session.covered_days:
        session.covered_days.append(question.day)


def _is_interview_complete(
    session: InterviewSession,
) -> bool:
    """
    Determine whether the interview has reached the planned
    minimum question requirement and has no remaining questions.

    The planner guarantees the target plan whenever enough
    curriculum data is available.
    """

    minimum_questions_reached = (
        len(session.evaluations)
        >= InterviewPlanner.MIN_QUESTIONS
    )

    current_question = _get_current_question(session)

    return (
        minimum_questions_reached
        and current_question is None
    )


def _generate_final_feedback(
    session: InterviewSession,
) -> FeedbackPayload:
    """
    Generate structured final interview feedback.
    """

    return feedback_engine.generate_feedback(
        candidate=session.candidate,
        evaluations=session.evaluations,
    )


def _create_session(
    request: InterviewRequest,
) -> InterviewSession:
    """
    Initialize a new interview session.
    """

    if request.candidate is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "The candidate field is required when "
                "starting a new interview session."
            ),
        )

    candidate = request.candidate

    plan = planner.create_plan(
        candidate=candidate,
        covered_days=[],
        asked_question_ids=[],
    )

    if not plan.questions:
        raise HTTPException(
            status_code=422,
            detail=(
                "Unable to create an interview plan for "
                "the supplied candidate."
            ),
        )

    session = InterviewSession(
        session_id=request.sessionId,
        candidate=candidate,
        plan=plan,
    )

    return session


# ============================================================
# Health Check
# ============================================================

@app.get("/")
def root() -> Dict[str, str]:
    """
    Basic service health endpoint.
    """

    return {
        "status": "ok",
        "service": "AI Interview Agent",
    }


# ============================================================
# Main Interview Endpoint
# ============================================================

@app.post(
    "/api/interview",
    response_model=InterviewResponse,
)
def interview(
    request: InterviewRequest,
) -> InterviewResponse:
    """
    Main multi-turn interview endpoint.

    First request:
        sessionId + candidate

    Subsequent requests:
        sessionId + message

    Final response:
        reply + done=true + structured feedback
    """

    session_id = request.sessionId.strip()

    if not session_id:
        raise HTTPException(
            status_code=400,
            detail="sessionId must not be empty.",
        )

    # ========================================================
    # Start a New Interview
    # ========================================================

    if session_id not in SESSIONS:

        session = _create_session(request)

        SESSIONS[session_id] = session

        first_question = _get_current_question(session)

        if first_question is None:
            session.done = True

            feedback = _generate_final_feedback(
                session
            )

            return InterviewResponse(
                reply="Interview completed.",
                done=True,
                feedback=feedback,
            )

        _record_question(
            session=session,
            question=first_question,
        )

        session.conversation.append(
            {
                "role": "assistant",
                "content": first_question.prompt,
            }
        )

        return InterviewResponse(
            reply=(
                "Welcome to your technical interview. "
                "Let's begin.\n\n"
                f"{first_question.prompt}"
            ),
            done=False,
            feedback=None,
        )

    # ========================================================
    # Existing Session
    # ========================================================

    session = SESSIONS[session_id]

    if session.done:
        raise HTTPException(
            status_code=409,
            detail="This interview session has already completed.",
        )

    # A message is required for every subsequent turn.

    if request.message is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "message is required for an existing "
                "interview session."
            ),
        )

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="message must not be empty.",
        )

    # ========================================================
    # Get Current Question
    # ========================================================

    current_question = None

    if session.asked_question_ids:
        current_index = session.current_question_index - 1

        if (
            0 <= current_index
            < len(session.plan.questions)
        ):
            current_question = session.plan.questions[
                current_index
            ]

    if current_question is None:
        raise HTTPException(
            status_code=500,
            detail=(
                "Interview state is inconsistent: "
                "no current question could be determined."
            ),
        )

    # ========================================================
    # Record Candidate Answer
    # ========================================================

    session.conversation.append(
        {
            "role": "user",
            "content": message,
        }
    )

    # ========================================================
    # Evaluate Answer
    # ========================================================

    evaluator = AnswerEvaluator(
        candidate=session.candidate,
    )

    evaluation = evaluator.evaluate_answer(
        question=current_question,
        answer=message,
    )

    session.evaluations.append(evaluation)

    # Move beyond the question that has just been answered.

    session.current_question_index += 1

    # ========================================================
    # Follow-up Decision
    # ========================================================

    if evaluation.needs_follow_up:

        follow_up = planner.create_follow_up(
            parent_question=current_question,
            candidate_answer=message,
        )

        if follow_up is not None:
            # Do not count the follow-up as a separate
            # curriculum question slot in the base plan.
            #
            # It is still recorded in asked_question_ids
            # so conversation state remains consistent.

            _record_question(
                session=session,
                question=follow_up,
            )

            session.conversation.append(
                {
                    "role": "assistant",
                    "content": follow_up.prompt,
                }
            )

            return InterviewResponse(
                reply=follow_up.prompt,
                done=False,
                feedback=None,
            )

    # ========================================================
    # Check Completion
    # ========================================================

    if _is_interview_complete(session):

        session.done = True

        feedback = _generate_final_feedback(
            session
        )

        session.conversation.append(
            {
                "role": "assistant",
                "content": "Interview completed.",
            }
        )

        return InterviewResponse(
            reply="Interview completed.",
            done=True,
            feedback=feedback,
        )

    # ========================================================
    # Ask Next Question
    # ========================================================

    next_question = _get_current_question(session)

    if next_question is None:

        # Safety fallback:
        # If no question remains, end the interview.

        session.done = True

        feedback = _generate_final_feedback(
            session
        )

        session.conversation.append(
            {
                "role": "assistant",
                "content": "Interview completed.",
            }
        )

        return InterviewResponse(
            reply="Interview completed.",
            done=True,
            feedback=feedback,
        )

    _record_question(
        session=session,
        question=next_question,
    )

    session.conversation.append(
        {
            "role": "assistant",
            "content": next_question.prompt,
        }
    )

    return InterviewResponse(
        reply=next_question.prompt,
        done=False,
        feedback=None,
    )


# ============================================================
# Development Entry Point
# ============================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )




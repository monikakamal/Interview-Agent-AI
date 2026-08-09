"""
API Router defining HTTP endpoints for the AI Technical Interview Agent.
Exact match for Technical Specification: POST /api/interview
"""

import traceback
from fastapi import APIRouter, Depends, HTTPException

from models.schemas import InterviewRequest, InterviewResponse
from rag.retriever import RAGRetriever
from services.interview_service import InterviewService
from utils.logger import logger

router = APIRouter()

# Global Singleton Services
retriever_instance = RAGRetriever()
interview_service_instance = InterviewService(retriever=retriever_instance)


def get_interview_service() -> InterviewService:
    """Dependency injection provider for InterviewService."""
    return interview_service_instance


@router.post(
    "/api/interview",
    response_model=InterviewResponse,
    summary="Main Multi-Turn Technical Interview Endpoint",
    description=(
        "Conducted via multi-turn conversations using sessionId.\n"
        "- First request: sessionId + candidate (or candidateId)\n"
        "- Turn requests: sessionId + message\n"
        "- Final response: reply + done=true + feedback object"
    ),
)
@router.post(
    "/api/interview/",
    response_model=InterviewResponse,
    include_in_schema=False,
)
def interview_endpoint(
    request: InterviewRequest,
    service: InterviewService = Depends(get_interview_service),
) -> InterviewResponse:
    """
    Main HTTP endpoint for the AI Interview Agent adhering to technical specification.
    Includes verbose execution tracing and full traceback logging on failure.
    """
    logger.info("-> Entering interview_endpoint()")
    logger.info(f"Request received: sessionId='{request.sessionId}', candidateId='{request.candidateId}', candidate_obj={request.candidate is not None}, message_len={len(request.message) if request.message else 0}")

    try:
        response = service.process_interview_request(request)
        logger.info(f"Returning InterviewResponse: done={response.done}, reply_len={len(response.reply)}")
        return response
    except HTTPException as http_exc:
        logger.warning(f"HTTPException raised in interview_endpoint [status={http_exc.status_code}]: {http_exc.detail}")
        raise http_exc
    except Exception as exc:
        logger.error(f"CRITICAL: Unhandled exception in interview_endpoint:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal Server Error: {str(exc)}",
        )

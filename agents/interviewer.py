"""
AI Interviewer Agent responsible for conducting realistic multi-turn technical interviews.
Uses RAG retrieved context, candidate learning history, and adaptive difficulty.
Includes robust Gemini LLM integration with automatic exponential retry and template fallback.
"""

import time
from typing import Dict, List, Optional
from google import genai

from agents.planner import PlannedQuestion
from memory.session_memory import SessionMemory
from utils.constants import DIFFICULTY_EASY, DIFFICULTY_HARD, DIFFICULTY_MEDIUM
from utils.logger import logger


class InterviewerAgent:
    """
    Senior AI Technical Interviewer.
    Synthesizes natural, realistic, probing technical interview questions.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None) -> None:
        from app.config import settings
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model_name = model_name if model_name is not None else settings.llm_model_name
        self.max_retries = settings.max_retries
        self.retry_delay_seconds = settings.retry_delay_seconds
        self.client: Optional[genai.Client] = None
        if self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception as exc:
                logger.warning(f"Could not initialize Gemini Client: {exc}")

    def generate_question(
        self,
        session: SessionMemory,
        planned_question: PlannedQuestion,
        rag_context: str,
    ) -> str:
        """
        Generates a natural, realistic technical interview question using RAG context.
        """
        candidate_name = session.candidate.member.name
        job_role = session.candidate.member.jobRole or "AI Engineer"
        difficulty = session.current_difficulty

        system_instruction = (
            "You are a Senior AI Technical Interviewer conducting a live, realistic technical interview.\n"
            "Your tone is encouraging, professional, and rigorous. Speak like a lead engineer.\n"
            "Never sound robotic or scripted. Ask about trade-offs, architecture, edge cases, or real-world implementation.\n"
            "Keep questions focused, clear, and direct (1 to 3 sentences maximum)."
        )

        prompt = (
            f"Candidate: {candidate_name} ({job_role})\n"
            f"Topic: Day {planned_question.day} - {planned_question.topic}\n"
            f"Target Difficulty: {difficulty.upper()}\n"
            f"Retrieved RAG Curriculum Context:\n{rag_context}\n\n"
            f"Interview History Context:\n{session.get_conversation_history_context()}\n\n"
            f"Task: Formulate the next technical interview question for {candidate_name} based on the retrieved context. "
            f"Ask about how they would approach implementing {planned_question.topic}, what trade-offs exist, or why they would choose specific tools."
        )

        # Attempt Gemini LLM Generation with Retries
        if self.client and self.api_key:
            llm_reply = self._call_llm_with_retry(system_instruction, prompt)
            if llm_reply:
                return llm_reply

        # Fallback Generator
        return self._fallback_question(planned_question, rag_context, difficulty)

    def generate_follow_up(
        self,
        session: SessionMemory,
        parent_question: PlannedQuestion,
        candidate_answer: str,
        score: float,
        rag_context: str,
    ) -> str:
        """
        Generates an adaptive follow-up question based on candidate answer quality.
        - High Score: Increase difficulty, ask about system limits or trade-offs.
        - Weak Score: Ask an easier follow-up or clarification.
        - Low/Incorrect Score: Probe understanding of core principles.
        """
        candidate_name = session.candidate.member.name
        difficulty = session.current_difficulty

        if score >= 4.0:
            adaptive_goal = "The candidate gave a strong answer! Push them further: ask about scaling, edge cases, or production trade-offs."
        elif score < 2.5:
            adaptive_goal = "The candidate's answer showed misunderstanding. Probe their understanding of fundamental concepts gently."
        else:
            adaptive_goal = "The candidate's response was partial. Ask them to clarify their reasoning or explain an example."

        system_instruction = (
            "You are a Senior AI Technical Interviewer conducting an adaptive interview.\n"
            "Ask an intelligent, concise follow-up question that directly references what the candidate just said.\n"
            "Keep questions direct and conversational (1 to 2 sentences)."
        )

        prompt = (
            f"Candidate: {candidate_name}\n"
            f"Topic: {parent_question.topic}\n"
            f"Question Asked: {parent_question.prompt_template}\n"
            f"Candidate Answer: {candidate_answer}\n"
            f"Answer Score: {score:.1f}/5.0\n"
            f"Adaptive Strategy: {adaptive_goal}\n"
            f"RAG Context:\n{rag_context}\n\n"
            f"Task: Write a natural follow-up question."
        )

        if self.client and self.api_key:
            llm_reply = self._call_llm_with_retry(system_instruction, prompt)
            if llm_reply:
                return llm_reply

        return self._fallback_follow_up(parent_question, candidate_answer, score)

    def _call_llm_with_retry(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """
        Calls Gemini API with retries. On 429 quota exhaustion, immediately uses fallback.
        """
        for attempt in range(self.max_retries):
            try:
                full_contents = f"{system_prompt}\n\n{user_prompt}"
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_contents,
                )
                if response and response.text:
                    return response.text.strip()
            except Exception as exc:
                exc_str = str(exc)
                logger.warning(f"Gemini API attempt {attempt+1} encountered: {exc}")
                if "429" in exc_str or "RESOURCE_EXHAUSTED" in exc_str:
                    logger.info("Quota limit reached; using fallback interviewer engine.")
                    return None
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay_seconds * (2 ** attempt))
        return None

    def _fallback_question(self, q: PlannedQuestion, rag_context: str, difficulty: str) -> str:
        topic = q.topic
        day = q.day

        if difficulty == DIFFICULTY_HARD:
            return (
                f"Looking at {topic} (Day {day}), how would you design a scalable production pipeline around it, "
                f"and what critical trade-offs or failure modes would you monitor?"
            )
        elif difficulty == DIFFICULTY_EASY:
            return (
                f"Let's cover {topic} from Day {day}. Can you explain the core concept in simple terms and "
                f"why it's important in modern AI systems?"
            )

        return (
            f"Regarding Day {day} - {topic}: Can you explain your engineering approach to implementing this, "
            f"and why you would choose that architecture over alternatives?"
        )

    def _fallback_follow_up(self, q: PlannedQuestion, answer: str, score: float) -> str:
        topic = q.topic
        excerpt = answer[:120] + "..." if len(answer) > 120 else answer

        if score >= 4.0:
            return (
                f"That's a solid explanation of {topic}. What potential bottlenecks or limitations "
                f"might arise with your approach if system traffic or data volume increases 10x?"
            )
        elif score < 2.5:
            return (
                f"You mentioned '{excerpt}'. Can we step back and clarify the core principle behind {topic}? "
                f"How does it handle error cases or edge inputs?"
            )

        return (
            f"You noted '{excerpt}'. Could you walk me through a concrete example or explain the key trade-offs "
            f"of that choice in practice?"
        )

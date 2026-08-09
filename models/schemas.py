from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Candidate Schemas
# ============================================================

class MemberInfo(BaseModel):
    """
    Basic information about a candidate/member.
    Matches the structure used in candidates.json.
    """

    id: str
    name: str
    jobRole: Optional[str] = "AI Engineer"
    yearsExperience: Optional[int] = 0
    education: Optional[str] = None
    status: Optional[str] = None


class MissionInfo(BaseModel):
    """
    Information about a candidate's mission for a curriculum day.
    """

    day: int
    title: str
    passed: Optional[bool] = None
    attempts: Optional[int] = 1
    skipped: Optional[bool] = False


class SignalInfo(BaseModel):
    """
    Learning/activity signals for a candidate.
    """

    commitDays: Optional[int] = 0
    missionsCompleted: Optional[int] = 0
    missionsFirstTry: Optional[int] = 0


class CandidateProfile(BaseModel):
    """
    Complete candidate profile.

    Matches the candidate object structure in candidates.json.
    """

    member: MemberInfo
    missions: List[MissionInfo] = Field(default_factory=list)
    signals: Optional[SignalInfo] = None


class CandidatesData(BaseModel):
    """
    Root schema for candidates.json.

    Expected structure:

    {
        "candidates": [...]
    }
    """

    candidates: List[CandidateProfile] = Field(default_factory=list)


# ============================================================
# Curriculum Schemas
# ============================================================

class ModuleInfo(BaseModel):
    """
    Information about one curriculum module.
    """

    n: int
    title: str
    days: List[int] = Field(default_factory=list)


class CurriculumDay(BaseModel):
    """
    Information about one curriculum day.
    """

    day: int
    title: str
    type: str
    tools: List[str] = Field(default_factory=list)
    objectives: List[str] = Field(default_factory=list)


class CurriculumData(BaseModel):
    """
    Root schema for curriculum.json.

    Expected structure:

    {
        "cohort": "...",
        "modules": [...],
        "days": [...]
    }
    """

    cohort: str
    modules: List[ModuleInfo] = Field(default_factory=list)
    days: List[CurriculumDay] = Field(default_factory=list)


# ============================================================
# API Request / Response Schemas
# ============================================================

class InterviewRequest(BaseModel):
    """
    Request received by the interview API.
    """

    sessionId: Optional[str] = None
    candidateId: Optional[str] = None
    candidate: Optional[dict] = None
    message: Optional[str] = None


class FeedbackPayload(BaseModel):
    """
    Structured feedback generated after the interview.
    """

    summary: str
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    next: List[str] = Field(default_factory=list)


class InterviewResponse(BaseModel):
    """
    Response returned by the interview API.
    """

    reply: str
    done: bool
    feedback: Optional[FeedbackPayload] = None
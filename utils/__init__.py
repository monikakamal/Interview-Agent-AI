"""
Utils module package init.
"""

from utils.constants import (
    DIFFICULTY_EASY,
    DIFFICULTY_HARD,
    DIFFICULTY_MEDIUM,
    HIGH_SCORE_THRESHOLD,
    LOW_SCORE_THRESHOLD,
    MIN_CURRICULUM_DAYS,
    MIN_QUESTIONS,
)
from utils.logger import logger

__all__ = [
    "MIN_QUESTIONS",
    "MIN_CURRICULUM_DAYS",
    "DIFFICULTY_EASY",
    "DIFFICULTY_MEDIUM",
    "DIFFICULTY_HARD",
    "HIGH_SCORE_THRESHOLD",
    "LOW_SCORE_THRESHOLD",
    "logger",
]

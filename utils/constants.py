"""
Constants for the AI Interview Agent system.
"""

# Interview Rules & Thresholds
MIN_QUESTIONS: int = 8
MIN_CURRICULUM_DAYS: int = 4
MAX_FOLLOW_UPS_PER_QUESTION: int = 1

# Difficulty Levels
DIFFICULTY_EASY = "easy"
DIFFICULTY_MEDIUM = "medium"
DIFFICULTY_HARD = "hard"

VALID_DIFFICULTIES = {DIFFICULTY_EASY, DIFFICULTY_MEDIUM, DIFFICULTY_HARD}

# Score Thresholds for Adaptive Probing
HIGH_SCORE_THRESHOLD: float = 4.0
LOW_SCORE_THRESHOLD: float = 2.5
FOLLOW_UP_THRESHOLD: float = 3.5

# Evaluation Criteria Weights
SCORE_WEIGHT_CORRECTNESS: float = 0.30
SCORE_WEIGHT_DEPTH: float = 0.20
SCORE_WEIGHT_CLARITY: float = 0.15
SCORE_WEIGHT_EXAMPLES: float = 0.15
SCORE_WEIGHT_TERMINOLOGY: float = 0.10
SCORE_WEIGHT_CONFIDENCE: float = 0.10

# API Defaults
DEFAULT_HOST: str = "0.0.0.0"
DEFAULT_PORT: int = 8000

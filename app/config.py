"""
Configuration settings for the AI Interview Agent.
Supports production options for model, embedding, vector DB, and retries.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseModel):
    """
    Application configuration settings loaded from environment or defaults.
    """

    app_name: str = "AI Technical Interview Agent"
    version: str = "1.0.0"

    # API Keys
    gemini_api_key: str = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY", "")
    )

    # Models Configuration
    llm_model_name: str = Field(
        default_factory=lambda: os.getenv("LLM_MODEL_NAME", "gemini-2.0-flash")
    )
    embedding_model_name: str = Field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL_NAME", "models/gemini-embedding-001")
    )

    # Vector DB / Retriever Config ("memory", "tfidf", "gemini")
    vector_db_type: str = Field(
        default_factory=lambda: os.getenv("VECTOR_DB_TYPE", "memory")
    )

    # Resilience & Retries
    max_retries: int = Field(
        default_factory=lambda: int(os.getenv("MAX_RETRIES", "3"))
    )
    retry_delay_seconds: float = Field(
        default_factory=lambda: float(os.getenv("RETRY_DELAY_SECONDS", "1.0"))
    )

    # Data Paths
    candidates_path: Path = Field(
        default_factory=lambda: BASE_DIR / "data" / "candidates.json"
    )
    curriculum_path: Path = Field(
        default_factory=lambda: BASE_DIR / "data" / "curriculum.json"
    )


settings = Settings()

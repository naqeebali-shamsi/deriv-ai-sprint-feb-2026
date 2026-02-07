"""Centralized configuration via environment variables.

Uses pydantic-settings for validation and .env file support.
All hardcoded values across the project should reference this module.
"""
import os
from functools import lru_cache
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent


class Settings:
    """Application settings loaded from environment variables."""

    def __init__(self):
        # Server
        self.BACKEND_HOST: str = os.getenv("BACKEND_HOST", "127.0.0.1")
        self.BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
        self.STREAMLIT_PORT: int = int(os.getenv("STREAMLIT_PORT", "8501"))

        # Database
        self.DATABASE_PATH: str = os.getenv(
            "DATABASE_PATH", str(PROJECT_ROOT / "app.db")
        )

        # Ollama LLM
        self.OLLAMA_URL: str = os.getenv(
            "OLLAMA_URL", "http://localhost:11434"
        )
        self.OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        self.OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "30"))
        self.LLM_MULTI_AGENT: bool = os.getenv(
            "LLM_MULTI_AGENT", "false"
        ).lower() in ("1", "true", "yes", "on")
        self.LLM_MULTI_AGENT_ROLES: list[str] = os.getenv(
            "LLM_MULTI_AGENT_ROLES",
            "behavioral,network,compliance",
        ).split(",")

        # Simulator
        self.SIMULATOR_TPS: float = float(os.getenv("SIMULATOR_TPS", "1.0"))
        self.FRAUD_RATE: float = float(os.getenv("FRAUD_RATE", "0.10"))

        # CORS
        self.CORS_ORIGINS: list[str] = os.getenv(
            "CORS_ORIGINS", "*"
        ).split(",")

        # Logging
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
        self.LOG_FORMAT: str = os.getenv("LOG_FORMAT", "text")  # text or json

        # Models directory
        self.MODELS_DIR: str = os.getenv(
            "MODELS_DIR", str(PROJECT_ROOT / "models")
        )

        # Guardian Agent
        self.GUARDIAN_ENABLED: bool = os.getenv(
            "GUARDIAN_ENABLED", "true"
        ).lower() in ("1", "true", "yes", "on")
        self.GUARDIAN_CHECK_INTERVAL: int = int(
            os.getenv("GUARDIAN_CHECK_INTERVAL", "30")
        )
        self.GUARDIAN_MIN_LABELS: int = int(
            os.getenv("GUARDIAN_MIN_LABELS", "5")
        )

    @property
    def backend_url(self) -> str:
        return f"http://{self.BACKEND_HOST}:{self.BACKEND_PORT}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

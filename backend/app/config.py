"""Configuration settings for the FactShield Edu RAG application.

This module reads environment variables (and optional `.env` file) for
database URL, API credentials (Gemini, OpenAI), model provider selection,
and Hugging Face Hub tokens.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Pydantic model for application settings.

    Automatically reads environment variables prefixed with or matching
    the field names case-insensitively. Supports loading from a local .env file.
    """

    database_url: str = (
        "postgresql+asyncpg://factshield:password@localhost:5432/factshield"
    )
    gemini_api_key: str = ""
    openai_api_key: str = ""
    hf_token: str = ""
    
    # Model provider selection: "ollama", "openai", or "hybrid" (OpenAI with Ollama fallback)
    model_provider: str = "hybrid"
    
    # Token budget tracking and optimization
    enable_token_optimization: bool = True
    max_monthly_tokens: int = 100000  # ~$1-2 for gpt-3.5-turbo
    
    # Hybrid search settings
    enable_hybrid_search: bool = True
    vector_weight: float = 0.7  # Weight for vector search in hybrid (keyword gets 1-weight)

    # Latency controls
    low_latency_mode: bool = True
    external_search_timeout_seconds: float = 4.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

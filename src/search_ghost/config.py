"""Application settings loaded from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GHOST_", env_file=".env", extra="ignore")

    # KB path (local folder or s3://bucket/prefix)
    kb_path: str = "./kb"

    # LLM
    llm_model: str = "openai/gpt-4o-mini"
    llm_api_base: str = ""   # custom base URL, e.g. https://api.moonshot.cn/v1
    llm_api_key: str = ""    # explicit key (overrides OPENAI_API_KEY for this model)

    # Embedding
    embedding_model: str = "openai/text-embedding-3-small"
    embedding_dim: int = 1536
    embedding_api_base: str = ""   # custom base URL for embedding provider
    embedding_api_key: str = ""    # explicit key for embedding provider

    # Chunking
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Retrieval
    top_k: int = 6
    rrf_k: int = 60

    # Processing
    batch_threshold: int = 8
    worker_concurrency: int = 4

    # API keys (passed through to LiteLLM via env)
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Dev
    debug: bool = False
    log_level: str = "INFO"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

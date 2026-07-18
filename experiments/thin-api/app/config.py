from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SCRIBE_", extra="ignore")

    app_name: str = "Local Clinical Scribe"
    ollama_base_url: str = "http://127.0.0.1:11434"
    note_model: str = "medgemma:4b"
    whisper_model: str = "mlx-community/whisper-large-v3-turbo"
    max_audio_mb: int = Field(default=100, ge=1, le=500)
    allowed_origins: tuple[str, ...] = (
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()

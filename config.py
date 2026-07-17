from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Reuse the same .env that lives one folder up (Agent/.env) — no duplicated secrets.
ENV_PATH = Path(__file__).resolve().parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_PATH)

    openai_api_key: str
    llm_base_url: str | None = None   # None = public OpenAI; set only for Azure/internal gateway
    model: str = "gpt-4o-mini"
    max_agent_steps: int = 6

    # Gemini (Google AI Studio) — uses Google's OpenAI-compatible endpoint, so it
    # reuses the same AsyncOpenAI client shape as the rest of the project.
    gemini_api_key: str | None = None
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_model: str = "gemini-2.0-flash"

    # Vertex AI (Google Cloud, enterprise) — auth via a service account JSON file,
    # NOT a simple API key. Store the .json OUTSIDE this project folder and point
    # to it here with a full path — never commit that file.
    vertex_service_account_path: str | None = None
    vertex_project_id: str | None = None
    vertex_region: str = "us-central1"   # ⚠️ confirm this matches your TL's actual region
    vertex_model: str = "google/gemini-2.0-flash-001"


settings = Settings()

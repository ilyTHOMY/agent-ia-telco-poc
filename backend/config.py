from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM
    google_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    llm_max_tokens: int = 8192

    # PostgreSQL
    postgres_db: str = "agentia"
    postgres_user: str = "agentia"
    postgres_password: str = "agentia"
    database_url: str = "postgresql+asyncpg://agentia:agentia@postgres:5432/agentia"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection: str = "faq_mobile_money"
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"

    # WhatsApp
    whatsapp_verify_token: str = "mon_token_verification"
    whatsapp_access_token: str = ""

    # Email Gmail
    gmail_user: str = ""
    gmail_app_password: str = ""
    email_destinataire: str = ""

    # App
    env: str = "development"
    secret_key: str = "change_this_in_production"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

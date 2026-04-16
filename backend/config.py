from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    env: str = "development"
    secret_key: str = "change_me"
    log_level: str = "info"

    google_api_key: str = ""
    llm_model: str = "gemini-2.5-flash"
    llm_max_tokens: int = 8192

    database_url: str = ""
    redis_url: str = "redis://localhost:6379/0"

    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "knowledge_base"

    use_mock_apis: bool = True
    mock_data_path: str = "./data"

    whatsapp_api_key: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_verify_token: str = ""

    sendgrid_api_key: str = ""
    email_from: str = "support@agentia.ai"

    at_username: str = "sandbox"
    at_api_key: str = ""
    at_ussd_code: str = "#144#"

    class Config:
        env_file = ".env"

settings = Settings()

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "CineSense AI"
    environment: str = "development"
    database_url: str = "sqlite:///./cinesense.db"
    secret_key: str = "change-this-before-public-deployment"
    access_token_minutes: int = 720
    frontend_origin: str = "http://localhost:5173"
    enable_demo_account: bool = True
    chat_retention_days: int = 7
    llm_provider: str = "offline"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"
    enable_sentence_transformers: bool = False
    sentence_model: str = "all-MiniLM-L6-v2"
    tmdb_api_key: str = ""
    admin_api_key: str = "local-admin-change-me"
    admin_email: str = "admin@cinesense.ai"
    admin_password: str = "CineSenseAdmin!2026"
    public_api_url: str = "http://localhost:8000"
    max_upload_mb: int = 5
    login_max_failures: int = 5
    login_lock_minutes: int = 10
    b2b_api_key: str = "local-b2b-change-me"
    b2b_monthly_included_calls: int = 10000
    b2b_overage_per_1000_usd: float = 6.0
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_premium_price_id: str = ""
    stripe_family_price_id: str = ""
    public_app_url: str = "http://localhost:5173"
    enable_monitoring: bool = True
    enable_spacy_ner: bool = False
    spacy_model: str = "en_core_web_sm"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/calendar/google/callback"
    calendar_default_day_start: int = 18
    calendar_default_day_end: int = 24
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache
def get_settings() -> Settings:
    return Settings()

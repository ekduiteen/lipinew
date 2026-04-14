"""Centralized settings — all values from environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    log_level: str = "INFO"
    app_url: str = "http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://lipi:lipi@postgres:5432/lipi"

    # Valkey (NOT Redis)
    valkey_url: str = "valkey://valkey:6379/0"

    # vLLM
    vllm_url: str = "http://vllm:8080"
    vllm_model: str = "lipi"
    vllm_timeout: float = 8.0

    # ML service (STT + TTS)
    ml_service_url: str = "http://ml:5001"
    ml_timeout: float = 10.0

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_audio: str = "lipi-audio"
    minio_bucket_tts: str = "lipi-tts"
    minio_secure: bool = False

    # Groq fallback
    groq_api_key: str = ""

    # Auth — env var is JWT_EXPIRY_HOURS, stored internally as minutes
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 720          # maps to JWT_EXPIRY_HOURS in .env
    google_client_id: str = ""
    google_client_secret: str = ""

    @property
    def jwt_expire_minutes(self) -> int:
        return self.jwt_expiry_hours * 60


settings = Settings()

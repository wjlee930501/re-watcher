import json
from typing import Optional, List
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    # Database
    db_url: str = Field(alias="REV_DB_URL")
    db_pool_size: int = Field(default=5, alias="REV_DB_POOL_SIZE")  # Reduced from 10
    db_max_overflow: int = Field(default=10, alias="REV_DB_MAX_OVERFLOW")  # Reduced from 20

    # Redis
    redis_url: str = Field(alias="REV_REDIS_URL")

    # Crawler settings
    crawl_concurrency_default: int = Field(default=2, alias="REV_CRAWL_CONCURRENCY_DEFAULT")  # Reduced from 3
    playwright_headless: bool = Field(default=True, alias="REV_PLAYWRIGHT_HEADLESS")
    request_timeout_ms: int = Field(default=15000, alias="REV_REQUEST_TIMEOUT_MS")
    backoff_base_ms: int = Field(default=500, alias="REV_BACKOFF_BASE_MS")
    max_retry: int = Field(default=3, alias="REV_MAX_RETRY")
    snapshot_dir: str = Field(default="/data/snapshots", alias="REV_SNAPSHOT_DIR")
    snapshot_enabled: bool = Field(default=False, alias="REV_SNAPSHOT_ENABLED")  # Disable by default to save disk
    user_agent_pool: List[str] = Field(
        default=[
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        ],
        alias="REV_USER_AGENT_POOL"
    )
    quarantine_cooldown_hours: int = Field(default=6, alias="REV_QUARANTINE_COOLDOWN_HOURS")

    # Vercel
    vercel_allowed_origins: Optional[str] = Field(default=None, alias="VERCEL_ALLOWED_ORIGINS")
    internal_api_token: Optional[str] = Field(default=None, alias="REV_INTERNAL_API_TOKEN")

    # Sentiment Analysis
    transformers_cache: str = Field(default="/data/hf_cache", alias="TRANSFORMERS_CACHE")
    sentiment_batch_size: int = Field(default=16, alias="REV_SENTIMENT_BATCH_SIZE")  # Batch processing

    # Notification
    alim_provider: str = Field(default="nhn_bizmessage", alias="REV_ALIM_PROVIDER")
    alim_appkey: Optional[str] = Field(default=None, alias="REV_ALIM_APPKEY")
    alim_secret: Optional[str] = Field(default=None, alias="REV_ALIM_SECRET")
    alim_sender_key: Optional[str] = Field(default=None, alias="REV_ALIM_SENDER_KEY")
    alim_template_code: str = Field(default="RV_NEG_REVIEW_ALERT_01", alias="REV_ALIM_TEMPLATE_CODE")
    alim_idempotency_ttl_min: int = Field(default=10, alias="REV_ALIM_IDEMPOTENCY_TTL_MIN")
    quiet_hours_start: str = Field(default="22:00", alias="REV_QUIET_HOURS_START")
    quiet_hours_end: str = Field(default="08:00", alias="REV_QUIET_HOURS_END")
    callback_verify_token: Optional[str] = Field(default=None, alias="REV_CALLBACK_VERIFY_TOKEN")

    # Performance
    log_level: str = Field(default="INFO", alias="REV_LOG_LEVEL")

    @field_validator("user_agent_pool", mode="before")
    @classmethod
    def parse_user_agent_pool(cls, v):
        if isinstance(v, str):
            return json.loads(v)
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance to avoid re-parsing."""
    return Settings()


# Global settings instance
settings = get_settings()

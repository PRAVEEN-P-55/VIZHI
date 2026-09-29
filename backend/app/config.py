"""Application configuration and paths.

Central place for env-driven settings. Everything has a safe default so the
prototype boots with zero configuration for a live demo.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# ---- Filesystem layout -----------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent          # .../backend
PROJECT_ROOT = BACKEND_DIR.parent                             # .../VIZHI
DATASETS_DIR = PROJECT_ROOT / "Datasets"                      # provided CSVs
ARTIFACTS_DIR = BACKEND_DIR / "artifacts"                     # trained models
ARTIFACTS_DIR.mkdir(exist_ok=True)


class Settings(BaseSettings):
    """Runtime settings; override via environment or a .env file."""

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        extra="ignore",
    )

    app_name: str = "VIZHI Predictive Intelligence Platform"
    # SQLite by default (lightweight demo). Swap DATABASE_URL for Postgres+PostGIS.
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'cyberwatch.db').as_posix()}"

    # JWT / auth
    jwt_secret: str = "vizhi-dev-secret-change-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 8
    refresh_token_days: int = 7

    # Alerts
    alert_dedup_window_minutes: int = 60
    redis_url: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    alert_email_from: str = ""
    alert_email_to: str = ""
    sms_webhook_url: str = ""
    alert_webhook_url: str = ""
    # Optional LLM for free-text agent Q&A. If unset -> offline templates only.
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"

    # CORS
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

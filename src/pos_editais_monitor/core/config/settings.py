"""Settings centralizado com pydantic-settings.

Carrega de .env e variaveis de ambiente. Imutavel apos `get_settings()`.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import EmailStr, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuracao global da aplicacao."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="PEM_",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App
    env: Literal["development", "staging", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    log_format: Literal["console", "json"] = "console"
    api_key: SecretStr = SecretStr("change-me")

    # ---- Database
    database_url: str = "postgresql+asyncpg://pem:pem@localhost:5432/pem"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ---- Redis
    redis_url: str = "redis://localhost:6379/0"

    # ---- Scraping
    http_timeout_seconds: int = 30
    http_max_retries: int = 5
    http_user_agent: str = Field(
        default=(
            "pos-editais-monitor/0.1 "
            "(+https://github.com/fabricioguidine/pos-editais-monitor; "
            "contact: fabricioguidine@gmail.com)"
        )
    )
    rate_limit_rps: float = 0.5
    respect_robots: bool = True
    playwright_headless: bool = True
    playwright_pool_size: int = 2

    # ---- LLM fallback
    llm_enabled: bool = True
    llm_provider: Literal["anthropic"] = "anthropic"
    llm_model: str = "claude-haiku-4-5-20251001"
    llm_confidence_threshold: float = 0.65
    llm_max_tokens: int = 1500
    anthropic_api_key: SecretStr = SecretStr("")

    # ---- Notifications (email primario)
    email_enabled: bool = True
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_from: EmailStr | None = None
    notify_to: EmailStr | None = None
    notify_only_on_match: bool = True
    notify_digest_cron: str = "0 7 * * *"

    telegram_enabled: bool = False
    telegram_bot_token: SecretStr = SecretStr("")
    telegram_chat_id: str = ""

    # ---- e-MEC
    emec_base_url: str = "https://emec.mec.gov.br"
    emec_cache_ttl_hours: int = 168
    emec_only_active: bool = True
    emec_only_public: bool = True

    # ---- Matching
    match_min_score: float = 0.70
    match_default_profile: str = "fabricio"
    match_require_free: bool = True

    # ---- Observability
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    prometheus_enabled: bool = True
    prometheus_port: int = 9090

    # ---- Scheduling
    scheduler_enabled: bool = True
    scheduler_default_interval_minutes: int = 180

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Acessor global cacheado das settings. Sempre prefira injetar via DI."""
    return Settings()

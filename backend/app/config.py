"""Runtime settings, read once from environment variables.

Every setting has a safe local default so `uvicorn app.main:app` works on a
laptop with no setup. In production (ENV=production) the app refuses to start
without a password and secret key.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _normalise_db_url(url: str) -> str:
    # Render and Neon hand out postgres:// URLs; SQLAlchemy wants an explicit driver.
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


@dataclass(frozen=True)
class Settings:
    env: str = "development"
    database_url: str = "sqlite:///./drop_studio.db"
    app_password: str = ""
    secret_key: str = "dev-secret-change-me"
    token_days: int = 30
    frontend_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    anthropic_timeout_s: float = 180.0
    max_upload_bytes: int = 5 * 1024 * 1024
    extra: dict = field(default_factory=dict)

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def auth_enabled(self) -> bool:
        return bool(self.app_password)

    @property
    def ai_enabled(self) -> bool:
        return bool(self.anthropic_api_key)

    def validate(self) -> None:
        if self.is_production:
            missing = [
                name
                for name, value in (
                    ("APP_PASSWORD", self.app_password),
                    ("SECRET_KEY", "" if self.secret_key == "dev-secret-change-me" else self.secret_key),
                )
                if not value
            ]
            if missing:
                raise RuntimeError(f"Missing required settings in production: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    origins = os.getenv("FRONTEND_ORIGIN", "")
    s = Settings(
        env=os.getenv("ENV", "development"),
        database_url=_normalise_db_url(os.getenv("DATABASE_URL", "sqlite:///./drop_studio.db")),
        app_password=os.getenv("APP_PASSWORD", ""),
        secret_key=os.getenv("SECRET_KEY", "dev-secret-change-me"),
        token_days=int(os.getenv("TOKEN_DAYS", "30")),
        frontend_origins=tuple(o.strip().rstrip("/") for o in origins.split(",") if o.strip())
        or Settings.frontend_origins,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
    )
    s.validate()
    return s

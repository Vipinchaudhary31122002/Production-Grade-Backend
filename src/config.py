"""
config.py — Application configuration via Pydantic Settings.

OOP concepts applied:
- Encapsulation: All environment-dependent settings are gathered inside a
  single ``Settings`` class. External code reads validated, typed attributes
  rather than raw ``os.getenv`` calls, hiding the env-file parsing details.
- Inheritance: ``Settings`` inherits from ``BaseSettings``, gaining automatic
  env-file loading, type coercion, and validation without re-implementing any
  of that infrastructure.
- Abstraction: The ``get_settings`` factory (cached with ``lru_cache``) is
  the only public surface callers need — they never instantiate ``Settings``
  directly.
- Single-Responsibility: Configuration concerns are isolated here; no other
  module owns env-var reading.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central store for every runtime configuration value.

    Values are read from the ``.env`` file and overridden by actual
    environment variables, giving a clean 12-factor-app approach.

    Attributes are type-annotated so Pydantic validates them on startup
    and raises an informative error if a required value is missing or has
    the wrong type.
    """

    # ── Application ───────────────────────────────────────────────────────
    APP_NAME: str = "MyApp"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "fallback-secret-key"

    # ── Database ──────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"

    # ── JWT ───────────────────────────────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # ── Derived helpers (encapsulation of computed properties) ────────────

    @property
    def is_production(self) -> bool:
        """Return True when running in a production environment."""
        return self.APP_ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Return True when running in a development environment."""
        return self.APP_ENV.lower() == "development"

    @property
    def is_sqlite(self) -> bool:
        """Return True if the configured database is SQLite."""
        return "sqlite" in self.DATABASE_URL.lower()


@lru_cache
def get_settings() -> Settings:
    """Return the shared, validated Settings instance (singleton via lru_cache)."""
    return Settings()


settings = get_settings()

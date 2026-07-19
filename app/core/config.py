from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str
    APP_ENV: str
    DEBUG: bool
    DB_NAME: str
    SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    ALLOWED_ORIGINS: list[str]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV.lower() == "development"
    
    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.DB_NAME}"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
from functools import lru_cache

from pydantic import Field
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ModuleNotFoundError:  # pragma: no cover - local test fallback
    from pydantic import BaseSettings  # type: ignore

    SettingsConfigDict = dict  # type: ignore


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    PAPERLESS_BASE_URL: str = Field(default='http://172.16.10.10:8000')
    PAPERLESS_TOKEN: str
    POOL_TAG_NAME: str = Field(default='Pool')
    SYNC_PAGE_SIZE: int = Field(default=100)
    SYNC_LOOKBACK_DAYS: int = Field(default=365)
    DATABASE_URL: str = Field(default='sqlite:////data/app.db')

    SCHEDULER_ENABLED: bool = Field(default=False)
    SCHEDULER_INTERVAL_MINUTES: int = Field(default=360)
    SCHEDULER_RUN_ON_STARTUP: bool = Field(default=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()

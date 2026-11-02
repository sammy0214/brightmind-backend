from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

REGIONS = {"africa", "us_uk_ca_au", "eu_br_in"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    region: str = "africa"
    database_url: str = "sqlite+aiosqlite:///./brightmind_dev.db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-only-change-me"
    parent_token_minutes: int = 60
    child_token_minutes: int = 720

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5-5"
    use_llm_moderation: bool = True

    consent_policy_version: str = "2026-01"
    storage_dir: str = "./data"
    auto_create_tables: bool = True


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if s.region not in REGIONS:
        raise ValueError(f"REGION must be one of {sorted(REGIONS)}")
    return s

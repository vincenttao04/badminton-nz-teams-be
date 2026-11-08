from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str

    # Session and cookie settings.
    session_cookie_name: str = "session"
    session_lifetime_hours: int = 12
    session_cookie_secure: bool = True
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    # Access code the seed assigns to the demo team. Override per environment;
    # the default is for local seeding only, not a real credential.
    seed_team_access_code: str = "badminton-demo-access"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]

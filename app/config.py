import hashlib
import os
from functools import lru_cache
from typing import Annotated

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables.

    API keys are configured as SHA-256 hex digests in API_KEY_HASHES. For local
    development only, plain keys may be supplied through DEV_API_KEYS and are
    hashed at startup.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Web Unlocker API"
    environment: str = "development"
    api_key_hashes: str = ""
    dev_api_keys: str = ""
    redis_url: str = "redis://redis:6379/0"
    cache_ttl_seconds: Annotated[int, Field(gt=0)] = 3600
    playwright_server_url: str = "ws://localhost:3000"
    browser_timeout_ms: Annotated[int, Field(gt=0)] = 15000
    request_rate_limit: str = "5/minute"
    max_proxy_attempts: Annotated[int, Field(gt=0)] = 3
    free_proxy_list: str = ""
    scrapingbee_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-3.5-turbo"
    cleaner_min_chars: Annotated[int, Field(gt=0)] = 100

    @property
    def allowed_key_hashes(self) -> set[str]:
        """Return configured API key hashes, including local dev plain keys."""

        hashes = {
            item.strip().lower()
            for item in self.api_key_hashes.split(",")
            if item.strip()
        }
        hashes.update(
            hashlib.sha256(key.strip().encode("utf-8")).hexdigest()
            for key in self.dev_api_keys.split(",")
            if key.strip()
        )
        return hashes

    @property
    def proxies(self) -> list[str]:
        """Return configured proxy URLs from env or a mounted file path."""

        value = self.free_proxy_list.strip()
        if not value:
            return []
        if os.path.exists(value):
            with open(value, encoding="utf-8") as proxy_file:
                return [line.strip() for line in proxy_file if line.strip()]
        return [item.strip() for item in value.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings object for dependency injection."""

    return Settings()

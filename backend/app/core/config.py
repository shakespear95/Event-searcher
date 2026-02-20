"""
Application configuration using Pydantic Settings.
All config values come from environment variables.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Environment
    env: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "DEBUG"

    # LLM API Keys
    anthropic_api_key: str = Field(default="", description="Claude API key")
    openai_api_key: str = Field(default="", description="OpenAI API key (optional)")
    google_api_key: str = Field(default="", description="Gemini API key")

    # Search API Keys
    perplexity_api_key: str = Field(default="", description="Perplexity API key")
    serpapi_api_key: str = Field(default="", description="SerpAPI key")

    # Weather API (optional)
    openweather_api_key: str = Field(default="", description="OpenWeatherMap API key (optional)")

    # Proxy Configuration
    proxy_service: str = "brightdata"
    proxy_username: str = ""
    proxy_password: str = ""
    proxy_host: str = ""
    proxy_port: str = ""

    # Supabase (optional - not used yet)
    supabase_url: str = Field(default="", description="Supabase project URL (optional)")
    supabase_key: str = Field(default="", description="Supabase anon key (optional)")
    supabase_service_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: str = "http://localhost:3000,https://event-searcher.vercel.app,https://event-searcher-95-git-main-shakespears-projects.vercel.app,https://event-searcher-95-f4katcg7i-shakespears-projects.vercel.app"

    # Rate Limiting
    rate_limit_per_minute: int = 60
    rate_limit_per_day: int = 1000

    # Search Defaults
    default_results_count: int = 20
    default_radius_km: int = 25
    default_cache_ttl_seconds: int = 3600

    @field_validator("allowed_origins")
    @classmethod
    def parse_origins(cls, v: str) -> list[str]:
        """Parse comma-separated origins into list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def proxy_url(self) -> str | None:
        """Build proxy URL from components."""
        if not all([self.proxy_host, self.proxy_port]):
            return None
        if self.proxy_username and self.proxy_password:
            return f"http://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}"
        return f"http://{self.proxy_host}:{self.proxy_port}"

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

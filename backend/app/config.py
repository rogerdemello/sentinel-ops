"""Centralized configuration via pydantic-settings.

All external dependencies are optional: when Supabase or the LLM providers are
not configured, the app degrades gracefully (in-memory persistence, heuristic
RCA) so the full demo loop runs with zero external setup.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App ---
    app_name: str = "SentinelOps AI"
    environment: Literal["dev", "staging", "prod"] = "dev"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    # --- Simulator ---
    sim_tick_seconds: float = 2.0  # wall-clock seconds per simulation tick
    sim_minutes_per_tick: float = 1.0  # simulated minutes advanced per tick
    sim_autostart: bool = True

    # --- Supabase (optional) ---
    supabase_url: str | None = None
    supabase_service_key: str | None = None
    # Direct Postgres connection (preferred for write-through; bypasses PostgREST/RLS).
    database_url: str | None = None
    # Persist high-volume raw telemetry metrics to the DB (off by default — chatty).
    persist_telemetry: bool = False

    # --- Azure OpenAI (primary LLM) ---
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_api_version: str = "2024-06-01"
    azure_openai_deployment: str | None = None  # e.g. "gpt-4o"

    # --- Google Gemini (failover LLM) ---
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-pro"

    # --- LLM routing ---
    llm_primary: Literal["azure", "gemini"] = "azure"
    llm_max_retries: int = 2

    # --- Autonomous remediation (self-healing) ---
    # When enabled, the engine auto-executes remediation plans whose maximum action
    # risk is at/below ``auto_remediate_max_risk`` (others still await human approval).
    auto_remediate: bool = False
    auto_remediate_max_risk: Literal["low", "medium", "high", "critical"] = "low"

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)

    @property
    def db_persist_enabled(self) -> bool:
        return bool(self.database_url)

    @property
    def persistence_enabled(self) -> bool:
        return self.db_persist_enabled or self.supabase_enabled

    @property
    def azure_enabled(self) -> bool:
        return bool(
            self.azure_openai_endpoint
            and self.azure_openai_api_key
            and self.azure_openai_deployment
        )

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def any_llm_enabled(self) -> bool:
        return self.azure_enabled or self.gemini_enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()

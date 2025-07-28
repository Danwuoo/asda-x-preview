"""Configuration for ASDA-X Core Components."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional


class LoggerSettings(BaseSettings):
    """Configuration for the TraceLogger."""
    model_config = SettingsConfigDict(env_prefix='ASDA_LOGGER_')

    # Enable/disable sinks
    jsonl_enabled: bool = True
    sqlite_enabled: bool = True
    stream_enabled: bool = False # Disabled by default

    # Sink configurations
    jsonl_path: str = "data/trace_events.jsonl"
    sqlite_path: str = "data/asda_traces.db"
    stream_host: str = "127.0.0.1"
    stream_port: int = 5555


# Global settings instance
settings = LoggerSettings()

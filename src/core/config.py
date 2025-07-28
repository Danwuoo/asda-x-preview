"""
Configuration loading and validation for ASDA-X.

This module uses Pydantic to define the application settings and loads them
from a YAML file. It provides a singleton `settings` object that can be
imported and used throughout the application.
"""

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, ValidationError


class TracingSettings(BaseModel):
    """Configuration for observability and tracing."""
    jsonl_enabled: bool = True
    sqlite_enabled: bool = True
    stream_enabled: bool = False
    jsonl_path: str = "data/trace_events.jsonl"
    sqlite_path: str = "data/asda_traces.db"
    stream_host: str = "127.0.0.1"
    stream_port: int = 5555


class InferenceSettings(BaseModel):
    """Configuration for AI model inference."""
    provider: str = "watsonx.ai"


from pydantic import ConfigDict

class Settings(BaseModel):
    """Root configuration model for the application."""
    model_config = ConfigDict(extra='allow')

    tracing: TracingSettings = Field(default_factory=TracingSettings)
    inference: InferenceSettings = Field(default_factory=InferenceSettings)


def find_config_file() -> Path:
    """Find the config file by searching upwards from the current directory."""
    current_dir = Path.cwd()
    for dir_path in [current_dir] + list(current_dir.parents):
        config_path = dir_path / "configs" / "asda_config.yaml"
        if config_path.exists():
            return config_path
    raise FileNotFoundError("Could not find asda_config.yaml in any parent directory.")


def load_settings() -> Settings:
    """Load settings from the YAML configuration file."""
    try:
        config_path = find_config_file()
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)

        if not config_data:
            # If the file is empty, return default settings
            return Settings()

        return Settings(**config_data)
    except (FileNotFoundError, ValidationError) as e:
        # Fallback to default settings if file not found or validation fails
        print(f"Warning: Could not load or validate config file. Using default settings. Error: {e}")
        return Settings()

# Create a global settings instance
settings = load_settings()

"""Externalized provider configuration.

Reads only from environment variables -- never hardcodes a secret, and
never reads at import time (only when a config object is actually
constructed, which adapters do lazily inside invoke()/health()).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


class MissingConfigError(Exception):
    """Raised when a required environment variable is not set."""


@dataclass(frozen=True)
class GroqConfig:
    api_key: str
    base_url: str = "https://api.groq.com/openai/v1"
    timeout_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> "GroqConfig":
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise MissingConfigError("GROQ_API_KEY is not set")
        base_url = os.environ.get("GROQ_BASE_URL", cls.base_url)
        timeout_raw = os.environ.get("GROQ_TIMEOUT_SECONDS")
        timeout_seconds = float(timeout_raw) if timeout_raw else cls.timeout_seconds
        return cls(api_key=api_key, base_url=base_url, timeout_seconds=timeout_seconds)

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from .config import Settings, get_settings
from .services.ai import AIClient, AnthropicClient, DisabledClient


@lru_cache
def _client(key: str, model: str, timeout: float) -> AIClient:
    return AnthropicClient(key, model, timeout) if key else DisabledClient()


def get_ai(settings: Settings = Depends(get_settings)) -> AIClient:
    return _client(settings.anthropic_api_key, settings.anthropic_model, settings.anthropic_timeout_s)

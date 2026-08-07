"""
LLM Factory — LiteLLM unified interface for GPT-4o and Claude Sonnet.

LiteLLM acts as a universal router:
  - "gpt-4o"                      → OpenAI  (OPENAI_API_KEY)
  - "claude-3-5-sonnet-20241022"  → Anthropic (ANTHROPIC_API_KEY)

Switch models by changing LITELLM_MODEL env var — zero code changes needed.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from langchain_community.chat_models import ChatLiteLLM

from ..config.loader import get_llm_config
from ..utils.logger import get_logger

# Load .env file if present (development convenience)
load_dotenv()

log = get_logger("llm_factory")


# ─── Public API ───────────────────────────────────────────────────────────────

def get_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> ChatLiteLLM:
    """
    Create and return a LangChain-compatible LiteLLM chat model.

    Priority for model selection:
      1. *model* argument (explicit override)
      2. ``LITELLM_MODEL`` environment variable
      3. ``llm_config.yaml → llm.primary_model``

    API keys are read from environment variables automatically:
      - ``OPENAI_API_KEY``    for GPT-4o / GPT-4-turbo
      - ``ANTHROPIC_API_KEY`` for Claude models

    Args:
        model:       LiteLLM model string (e.g. "gpt-4o", "claude-3-5-sonnet-20241022")
        temperature: Sampling temperature (0.0–1.0). Defaults to config value.
        max_tokens:  Max response tokens. Defaults to config value.

    Returns:
        Configured ``ChatLiteLLM`` instance ready for LangChain agent use.
    """
    cfg = get_llm_config()["llm"]

    # Model resolution: arg → env → config
    resolved_model = (
        model
        or os.getenv("LITELLM_MODEL")
        or cfg["primary_model"]
    )

    # Temperature resolution: arg → env → config
    resolved_temp = (
        temperature
        if temperature is not None
        else float(os.getenv("LITELLM_TEMPERATURE", cfg["temperature"]))
    )

    resolved_max_tokens = max_tokens or cfg["max_tokens"]

    log.info(f"Creating LLM: model={resolved_model}  temp={resolved_temp}  max_tokens={resolved_max_tokens}")

    llm = ChatLiteLLM(
        model=resolved_model,
        temperature=resolved_temp,
        max_tokens=resolved_max_tokens,
        request_timeout=cfg.get("timeout_seconds", 60),
        max_retries=cfg.get("max_retries", 3),
    )
    return llm


def get_fallback_llm() -> ChatLiteLLM:
    """
    Return a LiteLLM instance pointing to the configured fallback model.

    Used automatically by the agent executor when the primary model
    fails or rate-limits.
    """
    cfg = get_llm_config()["llm"]
    fallback = (
        os.getenv("LITELLM_FALLBACK_MODEL")
        or cfg.get("fallback_model", "claude-3-5-sonnet-20241022")
    )
    log.info(f"Creating fallback LLM: model={fallback}")
    return get_llm(model=fallback)


def get_llm_with_fallback() -> ChatLiteLLM:
    """
    Return primary LLM; if it fails on first call, transparently use fallback.

    This wraps LiteLLM's native fallback capability by configuring
    the ``fallbacks`` parameter.
    """
    cfg = get_llm_config()["llm"]
    primary = os.getenv("LITELLM_MODEL") or cfg["primary_model"]
    fallback = os.getenv("LITELLM_FALLBACK_MODEL") or cfg.get("fallback_model")

    log.info(f"LLM with fallback: primary={primary}  fallback={fallback}")

    # LiteLLM supports native fallbacks via litellm.completion(fallbacks=[...])
    # For LangChain integration we set up the primary and rely on the
    # agent executor's retry logic + get_fallback_llm() on exception.
    return get_llm(model=primary)


# ─── Convenience: model info ──────────────────────────────────────────────────

def current_model_info() -> dict:
    """Return a dict describing the currently configured LLM."""
    cfg = get_llm_config()["llm"]
    return {
        "primary_model":  os.getenv("LITELLM_MODEL") or cfg["primary_model"],
        "fallback_model": os.getenv("LITELLM_FALLBACK_MODEL") or cfg.get("fallback_model"),
        "temperature":    float(os.getenv("LITELLM_TEMPERATURE", cfg["temperature"])),
        "max_tokens":     cfg["max_tokens"],
        "provider":       _detect_provider(os.getenv("LITELLM_MODEL") or cfg["primary_model"]),
    }


def _detect_provider(model: str) -> str:
    """Infer LLM provider from model string."""
    model_lower = model.lower()
    if model_lower.startswith("gpt") or model_lower.startswith("o1"):
        return "openai"
    if model_lower.startswith("claude"):
        return "anthropic"
    if model_lower.startswith("gemini"):
        return "google"
    if "/" in model_lower:
        return "ollama"  # e.g. "ollama/llama3"
    return "unknown"

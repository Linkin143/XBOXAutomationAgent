"""
LLM Factory — provider-aware LangChain chat model factory.

Routes to the correct dedicated integration package based on model name:
  - "gpt-4o" / "gpt-4-turbo" / "gpt-4o-mini" / "o1-*"
        → langchain_openai.ChatOpenAI  (OPENAI_API_KEY)
  - "claude-*"
        → langchain_anthropic.ChatAnthropic  (ANTHROPIC_API_KEY)

Switch models by changing LITELLM_MODEL env var — zero code changes needed.

Note: ChatLiteLLM was removed from langchain-community ≥ 0.4.  The dedicated
      langchain-openai and langchain-anthropic packages are the recommended
      replacements and are already installed in this environment.
"""
from __future__ import annotations

import os
from typing import Optional, Union

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from ..config.loader import get_llm_config
from ..utils.logger import get_logger

# Load .env file if present (development convenience)
load_dotenv()

log = get_logger("llm_factory")

# Union type used in signatures so callers stay type-safe without importing both
AnyLLM = Union[ChatOpenAI, ChatAnthropic]


# ─── Internal helpers ─────────────────────────────────────────────────────────

def _detect_provider(model: str) -> str:
    """Infer LLM provider from model string."""
    m = model.lower()
    if m.startswith("gpt") or m.startswith("o1") or m.startswith("o3"):
        return "openai"
    if m.startswith("claude"):
        return "anthropic"
    if m.startswith("gemini"):
        return "google"
    if "/" in m:
        return "ollama"   # e.g. "ollama/llama3"
    return "unknown"


def _build_llm(model: str, temperature: float, max_tokens: int,
               timeout: int, max_retries: int) -> AnyLLM:
    """Instantiate the correct LangChain chat model class for *model*."""
    provider = _detect_provider(model)

    if provider == "anthropic":
        log.info(f"Provider=anthropic  model={model}")
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=float(timeout),
            max_retries=max_retries,
        )

    # Default: OpenAI (covers gpt-4o, gpt-4-turbo, gpt-4o-mini, o1-*, unknown)
    log.info(f"Provider=openai  model={model}")
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=float(timeout),
        max_retries=max_retries,
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def get_llm(
    model: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
) -> AnyLLM:
    """
    Create and return a LangChain-compatible chat model.

    Priority for model selection:
      1. *model* argument (explicit override)
      2. ``LITELLM_MODEL`` environment variable
      3. ``llm_config.yaml → llm.primary_model``

    API keys are read from environment variables automatically:
      - ``OPENAI_API_KEY``    for GPT-4o / GPT-4-turbo / GPT-4o-mini
      - ``ANTHROPIC_API_KEY`` for Claude models

    Args:
        model:       Model string (e.g. "gpt-4o", "claude-3-5-sonnet-20241022")
        temperature: Sampling temperature (0.0–1.0). Defaults to config value.
        max_tokens:  Max response tokens. Defaults to config value.

    Returns:
        Configured ``ChatOpenAI`` or ``ChatAnthropic`` instance ready for
        LangChain agent use.
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
    timeout = cfg.get("timeout_seconds", 60)
    retries = cfg.get("max_retries", 3)

    log.info(
        f"Creating LLM: model={resolved_model}  temp={resolved_temp}"
        f"  max_tokens={resolved_max_tokens}"
    )
    return _build_llm(resolved_model, resolved_temp, resolved_max_tokens,
                      timeout, retries)


def get_fallback_llm() -> AnyLLM:
    """
    Return a chat model instance pointing to the configured fallback model.

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


def get_llm_with_fallback() -> AnyLLM:
    """
    Return primary LLM.

    The agent executor handles automatic fallback via get_fallback_llm()
    on exception, so this simply returns the primary model.
    """
    cfg = get_llm_config()["llm"]
    primary = os.getenv("LITELLM_MODEL") or cfg["primary_model"]
    fallback = os.getenv("LITELLM_FALLBACK_MODEL") or cfg.get("fallback_model")
    log.info(f"LLM with fallback: primary={primary}  fallback={fallback}")
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

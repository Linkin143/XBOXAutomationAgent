"""Config loader — reads YAML config files and caches them in memory."""
from __future__ import annotations
import yaml
from pathlib import Path
from functools import lru_cache

_CONFIG_DIR = Path(__file__).parent


@lru_cache(maxsize=1)
def get_hw_config() -> dict:
    """Load and cache hardware_config.yaml."""
    with open(_CONFIG_DIR / "hardware_config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def get_game_config() -> dict:
    """Load and cache game_config.yaml."""
    with open(_CONFIG_DIR / "game_config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def get_ocr_regions() -> dict:
    """Load and cache ocr_regions.yaml."""
    with open(_CONFIG_DIR / "ocr_regions.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def get_llm_config() -> dict:
    """Load and cache llm_config.yaml (LiteLLM model + agent settings)."""
    with open(_CONFIG_DIR / "llm_config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)

"""Game script registry — maps game names to their BaseGame subclasses."""
from __future__ import annotations
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .base_game import BaseGame

_REGISTRY: dict[str, type] = {}


def register(name: str):
    """Class decorator to register a game class by name."""
    def decorator(cls):
        _REGISTRY[name.lower()] = cls
        return cls
    return decorator


def get_game_instance(game_name: str, console: int = 1, **kwargs) -> "BaseGame":
    """Instantiate a registered game class by name."""
    key = game_name.lower()
    if key not in _REGISTRY:
        # Lazy-load all known game modules
        _load_all()
    if key not in _REGISTRY:
        raise ValueError(f"Unknown game: '{game_name}'. "
                         f"Available: {list(_REGISTRY.keys())}")
    from ..hardware.gimx_controller import GimxController
    from ..config.loader import get_hw_config
    cfg = get_hw_config().get("gimx", {})
    host = cfg.get("host", "127.0.0.1")
    port_c1 = cfg.get("port_c1", 51914)
    port_c2 = cfg.get("port_c2", 51915)
    ctrl1 = GimxController(host=host, port=port_c1)
    ctrl2 = GimxController(host=host, port=port_c2)
    return _REGISTRY[key](ctrl1=ctrl1, ctrl2=ctrl2, console=console, **kwargs)


def _load_all():
    """Import all game modules to trigger their @register decorators."""
    from . import celeste, gears5, hollow_knight, sea_of_stars  # noqa: F401
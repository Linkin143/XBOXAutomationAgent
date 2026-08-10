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
    from ..hardware.gimx_controller import GimxController, GimxConfig
    from ..config.loader import get_hw_config
    gimx = get_hw_config().get("gimx", {})
    c1 = gimx.get("controller_1", {})
    c2 = gimx.get("controller_2", {})
    ctrl1 = GimxController(config=GimxConfig(
        host=c1.get("host", "127.0.0.1"),
        port=c1.get("port", 51914),
        com_port=c1.get("com_port", "COM8"),
    ))
    ctrl2 = GimxController(config=GimxConfig(
        host=c2.get("host", "127.0.0.1"),
        port=c2.get("port", 51915),
        com_port=c2.get("com_port", "COM6"),
    ))
    return _REGISTRY[key](ctrl1=ctrl1, ctrl2=ctrl2, console=console, **kwargs)


def _load_all():
    """Import all game modules to trigger their @register decorators."""
    from . import celeste, gears5, hollow_knight, sea_of_stars  # noqa: F401
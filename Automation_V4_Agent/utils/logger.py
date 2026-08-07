"""Logging setup using loguru — replaces V3 eDAT logging."""
from __future__ import annotations
import sys
from pathlib import Path
from loguru import logger

_INITIALIZED = False


def setup_logging(log_dir: str = "logs", level: str = "DEBUG") -> None:
    """Configure loguru sinks: console + rotating file."""
    global _INITIALIZED
    if _INITIALIZED:
        return
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger.remove()  # Remove default sink
    # Console sink — INFO and above
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> — <level>{message}</level>",
        colorize=True,
    )
    # File sink — DEBUG and above, rotate 10 MB
    logger.add(
        log_path / "automation_v4_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{line} — {message}",
        encoding="utf-8",
    )
    _INITIALIZED = True


def get_logger(name: str = "automation_v4"):
    """Return a contextualised loguru logger bound to *name*."""
    setup_logging()
    return logger.bind(name=name)

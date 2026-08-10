"""Logging setup using loguru — replaces V3 eDAT logging."""
from __future__ import annotations
import sys
import io
from pathlib import Path
from loguru import logger

# Wrap stdout in UTF-8 so emoji / arrow characters don't crash on Windows
# terminals that default to cp1252.  This is a no-op on systems already UTF-8.
_stdout_utf8 = io.TextIOWrapper(
    sys.stdout.buffer,
    encoding="utf-8",
    errors="replace",
    line_buffering=True,
) if hasattr(sys.stdout, "buffer") else sys.stdout

_INITIALIZED = False


def setup_logging(log_dir: str = "logs", level: str = "DEBUG") -> None:
    """Configure loguru sinks: console + rotating file."""
    global _INITIALIZED
    if _INITIALIZED:
        return
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger.remove()  # Remove default sink
    # Console sink — INFO and above, via UTF-8 wrapper so emoji/arrows render
    # correctly on Windows terminals that default to cp1252.
    logger.add(
        _stdout_utf8,
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

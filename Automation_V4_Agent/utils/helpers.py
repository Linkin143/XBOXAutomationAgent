"""Shared utility helpers for Automation V4."""
from __future__ import annotations
import time
import functools
from datetime import datetime
from typing import Callable, TypeVar, Any

T = TypeVar("T")


def retry(times: int = 3, delay_ms: int = 1000, exceptions: tuple = (Exception,)):
    """Decorator: retry a function *times* times on *exceptions*."""
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs) -> T:
            last_exc: Exception | None = None
            for attempt in range(1, times + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt < times:
                        time.sleep(delay_ms / 1000.0)
            raise last_exc  # type: ignore[misc]
        return wrapper
    return decorator


def wait_ms(milliseconds: int) -> None:
    """Sleep for *milliseconds* ms — replaces V3 Start-Sleep -Milliseconds."""
    time.sleep(milliseconds / 1000.0)


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp *value* between *minimum* and *maximum*."""
    return max(minimum, min(maximum, value))


def timestamp_str(fmt: str = "%Y%m%d_%H%M%S") -> str:
    """Return current local time formatted as *fmt*."""
    return datetime.now().strftime(fmt)


def ms_since(start: float) -> float:
    """Return milliseconds elapsed since *start* (from time.time())."""
    return (time.time() - start) * 1000.0

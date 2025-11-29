from typing import Callable, TypeVar, Any
from functools import wraps

from loguru import logger

T = TypeVar("T")


def safe_execute(default: T):
    """Decorator to catch exceptions and return a default value."""
    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return fn(*args, **kwargs)
            except Exception as exc:  # noqa: BLE001
                logger.error("safe_execute caught error in %s: %s", fn.__name__, exc)
                return default
        return wrapper
    return decorator

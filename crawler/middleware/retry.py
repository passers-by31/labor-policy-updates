"""指数退避重试。"""

import time
import random
import logging
from functools import wraps
from typing import Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable)


def retry(max_retries: int = 3, base_delay: float = 5.0) -> Callable[[F], F]:
    """指数退避重试装饰器。"""
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        delay = base_delay * (3 ** attempt) + random.uniform(0, 2)
                        logger.warning(
                            "%s 失败(第%d次), %.1fs后重试: %s",
                            func.__name__, attempt + 1, delay, e
                        )
                        time.sleep(delay)
            raise last_exception  # type: ignore
        return wrapper  # type: ignore
    return decorator

"""速率限制器。"""

import time
import random
from threading import Lock


class RateLimiter:
    """控制对同一站点的请求频率。"""

    def __init__(self, min_interval: float = 3.0, max_interval: float = 8.0):
        self._min = min_interval
        self._max = max_interval
        self._last_request: dict[str, float] = {}
        self._lock = Lock()

    def wait(self, source_id: str) -> None:
        """等待合适的时间后再发起请求。"""
        with self._lock:
            last = self._last_request.get(source_id, 0.0)
            elapsed = time.time() - last
            interval = random.uniform(self._min, self._max)
            if elapsed < interval:
                sleep_time = interval - elapsed
                time.sleep(sleep_time)
            self._last_request[source_id] = time.time()

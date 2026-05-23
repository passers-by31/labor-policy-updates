"""User-Agent 轮换池。"""

import random


class UserAgentPool:
    """User-Agent 轮换池。"""

    def __init__(self, agents: list[str] | None = None):
        self._agents = agents or [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        ]

    def get(self) -> str:
        """随机返回一个 User-Agent。"""
        return random.choice(self._agents)

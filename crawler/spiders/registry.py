"""Spider 注册表。"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crawler.spiders.base import Spider


class SpiderRegistry:
    """站点 ID 到 Spider 类的映射。"""

    def __init__(self):
        self._mapping: dict[str, type[Spider]] = {}

    def register(self, source_id: str, spider_cls: type[Spider]) -> None:
        """注册爬虫类。"""
        self._mapping[source_id] = spider_cls

    def get(self, source_id: str) -> type[Spider] | None:
        """获取爬虫类。"""
        return self._mapping.get(source_id)

    def all_source_ids(self) -> list[str]:
        return list(self._mapping.keys())

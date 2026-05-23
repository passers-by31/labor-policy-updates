"""省级站点爬虫（配置驱动，含 GBK 支持）。"""

from __future__ import annotations
from typing import Any
from urllib.parse import urljoin

from bs4 import Tag

from crawler.spiders.national import NationalSpider
from crawler.utils.encoding import to_utf8


class ProvinceSpider(NationalSpider):
    """省级站点爬虫，增加编码自动检测和转换。"""

    def _fetch(self, url: str) -> str | None:
        self.rate_limiter.wait(self.source_id)
        ua = self.ua_pool.get()
        try:
            resp = self._session.get(url, headers={"User-Agent": ua}, timeout=self.timeout)
            resp.raise_for_status()
            raw = resp.content
            return to_utf8(raw)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error("省级站点请求失败 %s: %s", url, e)
            return None

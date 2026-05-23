"""Spider 抽象基类。"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

import requests
from bs4 import BeautifulSoup

from crawler.middleware.rate_limiter import RateLimiter
from crawler.middleware.user_agent import UserAgentPool


class Spider(ABC):
    """爬虫基类。"""

    def __init__(
        self,
        source_config: dict[str, Any],
        rate_limiter: RateLimiter,
        ua_pool: UserAgentPool,
        timeout: int = 30,
    ):
        self.config = source_config
        self.source_id: str = source_config["id"]
        self.rate_limiter = rate_limiter
        self.ua_pool = ua_pool
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate",
        })

    def _fetch(self, url: str) -> str | None:
        """发送 GET 请求并返回文本内容。"""
        self.rate_limiter.wait(self.source_id)
        ua = self.ua_pool.get()
        try:
            resp = self._session.get(url, headers={"User-Agent": ua}, timeout=self.timeout)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except requests.RequestException as e:
            import logging
            logging.getLogger(__name__).error("请求失败 %s: %s", url, e)
            return None

    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "lxml")

    @abstractmethod
    def parse_list(self, html: str, list_config: dict[str, Any]) -> list[dict[str, str]]:
        """解析列表页，返回 [{title, url}]。"""
        ...

    @abstractmethod
    def parse_detail(self, html: str, base_url: str) -> dict[str, Any] | None:
        """解析详情页，返回 Policy dict。"""
        ...

    def crawl(self) -> list[dict[str, Any]]:
        """执行爬取流程，返回政策列表。"""
        results: list[dict[str, Any]] = []
        for list_cfg in self.config.get("list_pages", []):
            list_url = list_cfg["url"]
            max_pages = list_cfg.get("max_pages", 3)
            for page_num in range(1, max_pages + 1):
                url = self._build_list_url(list_url, page_num, list_cfg)
                html = self._fetch(url)
                if not html:
                    continue
                entries = self.parse_list(html, list_cfg)
                if not entries:
                    break
                for entry in entries:
                    detail_url = entry.get("url", "")
                    if not detail_url:
                        continue
                    detail_html = self._fetch(detail_url)
                    if not detail_html:
                        continue
                    policy = self.parse_detail(detail_html, detail_url)
                    if policy:
                        policy["sourceId"] = self.source_id
                        policy["sourceName"] = self.config.get("name", "")
                        results.append(policy)
        return results

    def _build_list_url(self, base_url: str, page_num: int, cfg: dict[str, Any]) -> str:
        """构造分页 URL。"""
        if page_num == 1:
            return base_url
        page_param = cfg.get("page_param", "index.html")
        if page_param in base_url:
            return base_url.replace(page_param, f"index_{page_num}.html")
        return base_url

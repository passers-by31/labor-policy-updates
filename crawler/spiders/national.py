"""国家级其他站点通用爬虫（配置驱动）。"""

from __future__ import annotations
from typing import Any
from urllib.parse import urljoin

from bs4 import Tag

from crawler.spiders.base import Spider
from crawler.parsers.date import parse_chinese_date
from crawler.parsers.content import extract_content


class NationalSpider(Spider):
    """配置驱动的国家级站点爬虫。"""

    def parse_list(self, html: str, list_config: dict[str, Any]) -> list[dict[str, str]]:
        soup = self._soup(html)
        base_url = self.config["base_url"]
        entries: list[dict[str, str]] = []
        selector = list_config.get("list_selector", "ul.list li a")
        for a in soup.select(selector):
            if not isinstance(a, Tag):
                continue
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if not href or not title:
                continue
            full_url = urljoin(base_url, href)
            entries.append({"title": title, "url": full_url})
        return entries

    def parse_detail(self, html: str, base_url: str) -> dict[str, Any] | None:
        soup = self._soup(html)
        rules = self.config.get("detail_rules", {})

        # 标题
        title = ""
        title_sel = rules.get("title_selector", "h1")
        el = soup.select_one(title_sel)
        if el:
            title = el.get_text(strip=True)
        if not title:
            return None

        # 日期
        publish_date = ""
        date_sel = rules.get("publish_date_selector", "")
        if date_sel:
            el = soup.select_one(date_sel)
            if el:
                publish_date = parse_chinese_date(el.get_text(strip=True))

        # 正文
        content_sel = rules.get("content_selector", "")
        content = extract_content(html, content_sel) if content_sel else extract_content(html)
        if not content:
            return None

        # 文号
        doc_number = ""
        doc_sel = rules.get("document_number_selector", "")
        if doc_sel:
            el = soup.select_one(doc_sel)
            if el:
                from crawler.parsers.document_number import extract_document_number
                doc_number = extract_document_number(el.get_text(strip=True)) or ""

        import hashlib
        raw = f"{base_url}_{publish_date or ''}"
        policy_id = f"{self.source_id}-{hashlib.md5(raw.encode()).hexdigest()[:8]}"

        return {
            "id": policy_id,
            "title": title,
            "url": base_url,
            "documentNumber": doc_number,
            "publishDate": publish_date or "",
            "effectiveDate": None,
            "category": "",
            "tags": [],
            "regions": ["全国"],
            "issuingAuthority": self.config.get("name", ""),
            "status": "effective",
            "summary": content[:200] if len(content) > 200 else content,
            "content": content,
            "contentHtml": None,
        }

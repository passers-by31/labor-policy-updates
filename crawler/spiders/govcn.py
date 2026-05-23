"""国务院爬虫。"""

from __future__ import annotations
from typing import Any
from urllib.parse import urljoin

from bs4 import Tag

from crawler.spiders.base import Spider
from crawler.parsers.date import parse_chinese_date
from crawler.parsers.document_number import extract_document_number
from crawler.parsers.content import extract_content


class GovcnSpider(Spider):
    """中央人民政府（国务院）爬虫。"""

    def parse_list(self, html: str, list_config: dict[str, Any]) -> list[dict[str, str]]:
        soup = self._soup(html)
        base_url = self.config["base_url"]
        entries: list[dict[str, str]] = []
        selector = list_config.get("list_selector", "div.news_box ul li a")
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

        # 标题
        title = ""
        for sel in ["div#UCAP-CONTENT h1", "div.content h1", "h1"]:
            el = soup.select_one(sel)
            if el:
                title = el.get_text(strip=True)
                break
        if not title:
            return None

        # 日期
        publish_date = ""
        for sel in ["div.fbtime span", "span.date", "div.info span"]:
            el = soup.select_one(sel)
            if el:
                publish_date = parse_chinese_date(el.get_text(strip=True))
                if publish_date:
                    break

        # 正文
        content = extract_content(html, "div#UCAP-CONTENT, div.TRS_Editor, div.pages_content")
        if not content:
            return None

        # 文号
        doc_number = ""
        for sel in ["div.xx_con", "div.info"]:
            el = soup.select_one(sel)
            if el:
                doc_number = extract_document_number(el.get_text(strip=True)) or ""

        import hashlib
        raw = f"{base_url}_{publish_date or ''}"
        policy_id = f"govcn-{hashlib.md5(raw.encode()).hexdigest()[:8]}"

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
            "issuingAuthority": "国务院",
            "status": "effective",
            "summary": content[:200] if len(content) > 200 else content,
            "content": content,
            "contentHtml": None,
        }

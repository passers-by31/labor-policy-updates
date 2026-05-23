"""国家医疗保障局爬虫。"""

from __future__ import annotations
import logging
import hashlib
import re
from typing import Any
from urllib.parse import urljoin

from crawler.spiders.base import Spider
from crawler.parsers.date import parse_chinese_date
from crawler.parsers.content import extract_content
from crawler.parsers.document_number import extract_document_number

logger = logging.getLogger("crawler.nhsa")


class NhsaSpider(Spider):
    """国家医疗保障局爬虫。

    列表页使用 TRS jPage 系统，政策条目以内嵌 XML datastore 形式存储
    在 <script> 标签内，需要从 CDATA 中提取 <li> 条目。
    """

    def parse_list(self, html: str, list_config: dict[str, Any]) -> list[dict[str, str]]:
        """解析列表页：从内嵌 datastore XML 中提取政策条目。"""
        entries: list[dict[str, str]] = []
        base_url = self.config["base_url"]

        # 从 datastore XML 中提取所有 record CDATA
        records = re.findall(
            r"<record><!\[CDATA\[(.*?)\]\]></record>", html, re.DOTALL
        )
        for record in records:
            # 从 CDATA 中提取 <a> 链接和标题
            m = re.search(r'<a[^>]*href="([^"]*)"[^>]*title="([^"]*)"', record)
            if not m:
                m = re.search(r'<a[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', record)
            if m:
                href = m.group(1).strip()
                title = (m.group(2) if len(m.groups()) > 1 else m.group(1)).strip()
                if href and title:
                    full_url = urljoin(base_url, href)
                    entries.append({"title": title, "url": full_url})

        if not entries:
            logger.warning("未从 datastore 中找到条目")

        logger.info("列表页获取 %d 条", len(entries))
        return entries

    def parse_detail(self, html: str, base_url: str) -> dict[str, Any] | None:
        soup = self._soup(html)

        # 标题
        title = ""
        for sel in ["div.atricle-title", "h1"]:
            el = soup.select_one(sel)
            if el:
                title = el.get_text(strip=True)
                break
        if not title:
            logger.warning("未找到标题: %s", base_url)
            return None

        # 日期
        publish_date = ""
        el = soup.select_one("span.wzy-rq")
        if el:
            raw = el.get_text(strip=True)
            publish_date = parse_chinese_date(raw)
        if not publish_date:
            for meta in soup.find_all("meta"):
                name = (meta.get("name") or "").lower()
                if name in ("pubdate", "publishdate"):
                    publish_date = parse_chinese_date(meta.get("content", ""))
                    if publish_date:
                        break

        # 正文
        content = extract_content(html, "div#zoom")
        if not content:
            return None

        # 文号（nhsa 页面不常用，尝试从内容中提取）
        doc_number = extract_document_number(content[:500]) or ""

        raw = f"{base_url}_{publish_date or ''}"
        policy_id = f"nhsa-{hashlib.md5(raw.encode()).hexdigest()[:8]}"

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
            "issuingAuthority": "国家医疗保障局",
            "status": "effective",
            "summary": content[:200] if len(content) > 200 else content,
            "content": content,
            "contentHtml": None,
        }

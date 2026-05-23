"""国务院爬虫。"""

from __future__ import annotations
import json
import logging
import hashlib
import re
from datetime import datetime, timedelta
from typing import Any

from bs4 import Tag

from crawler.spiders.base import Spider
from crawler.parsers.date import parse_chinese_date
from crawler.parsers.document_number import extract_document_number
from crawler.parsers.content import extract_content

logger = logging.getLogger("crawler.govcn")

# 仅处理最近 90 天的政策
MAX_AGE_DAYS = 90
# 批处理大小：每次最多抓取 detail 页数量
MAX_DETAIL_FETCH = 150


class GovcnSpider(Spider):
    """中央人民政府（国务院）爬虫。"""

    def crawl(self) -> list[dict[str, Any]]:
        """重写 crawl 以支持 JSON API 列表、日期预过滤和限量抓取。"""
        results: list[dict[str, Any]] = []
        for list_cfg in self.config.get("list_pages", []):
            list_url = list_cfg["url"]
            html = self._fetch(list_url)
            if not html:
                continue
            entries = self.parse_list(html, list_cfg)
            if not entries:
                continue

            # 按日期预过滤：只保留最近 MAX_AGE_DAYS 天内的政策
            cutoff = datetime.now() - timedelta(days=MAX_AGE_DAYS)
            filtered = []
            for e in entries:
                pd = e.get("publishDate", "")
                if pd:
                    try:
                        d = datetime.strptime(pd, "%Y-%m-%d")
                        if d < cutoff:
                            continue
                    except ValueError:
                        pass
                filtered.append(e)
            logger.info(
                "日期过滤后: %d/%d 条（最近 %d 天）",
                len(filtered),
                len(entries),
                MAX_AGE_DAYS,
            )

            # 限量抓取 detail 页
            batch = filtered[:MAX_DETAIL_FETCH]
            logger.info("本次抓取 detail 页: %d 条", len(batch))

            for entry in batch:
                detail_url = entry.get("url", "")
                if not detail_url:
                    continue
                detail_html = self._fetch(detail_url)
                if not detail_html:
                    continue
                policy = self.parse_detail(detail_html, detail_url)
                if policy:
                    # 优先使用 JSON API 提供的发布日期
                    if not policy.get("publishDate") and entry.get("publishDate"):
                        policy["publishDate"] = entry["publishDate"]
                    policy["sourceId"] = self.source_id
                    policy["sourceName"] = self.config.get("name", "")
                    results.append(policy)
        return results

    def parse_list(self, html: str, list_config: dict[str, Any]) -> list[dict[str, str]]:
        """解析列表页。若响应为 JSON 则直接解析（最新政策 JSON API）。"""
        text = html.strip()
        if text.startswith("["):
            try:
                data = json.loads(text)
                entries: list[dict[str, str]] = []
                for item in data:
                    title = item.get("TITLE", "").strip()
                    url = item.get("URL", "").strip()
                    pub_date = item.get("DOCRELPUBTIME", "").strip()
                    if title and url:
                        entries.append({
                            "title": title,
                            "url": url,
                            "publishDate": pub_date,
                        })
                logger.info("JSON API 获取 %d 条政策", len(entries))
                return entries
            except json.JSONDecodeError:
                logger.warning("JSON 解析失败，回退 HTML 解析")

        # 回退：HTML 解析
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
            from urllib.parse import urljoin
            full_url = urljoin(base_url, href)
            entries.append({"title": title, "url": full_url})
        return entries

    def parse_detail(self, html: str, base_url: str) -> dict[str, Any] | None:
        soup = self._soup(html)

        # 标题
        title = ""
        for sel in ["div.share-title", "div#UCAP-CONTENT h1", "div.content h1", "h1"]:
            el = soup.select_one(sel)
            if el:
                title = el.get_text(strip=True)
                break
        if not title:
            logger.warning("未找到标题: %s", base_url)
            return None

        # 日期：从表格中找"发布日期"所在行
        publish_date = ""
        # 方法1：查找包含"发布日期"的 td 的下一个 td
        for td in soup.find_all("td"):
            if "发布日期" in td.get_text():
                sibling = td.find_next_sibling("td")
                if sibling:
                    publish_date = parse_chinese_date(sibling.get_text(strip=True))
                    if publish_date:
                        break
        # 方法2：查找包含"发布日期"的 p/h2 标签
        if not publish_date:
            for tag in soup.find_all(["p", "h2"]):
                if "发布日期" in tag.get_text():
                    # 取冒号后的内容
                    raw = tag.get_text(strip=True)
                    m = re.search(r"发布日期[：:]\s*(.+)", raw)
                    if m:
                        publish_date = parse_chinese_date(m.group(1))
                        if publish_date:
                            break
        # 方法3：查找 meta 标签
        if not publish_date:
            for meta in soup.find_all("meta"):
                name = (meta.get("name") or "").lower()
                if name in ("publishdate", "pubdate"):
                    publish_date = parse_chinese_date(meta.get("content", ""))
                    if publish_date:
                        break

        # 正文
        content = extract_content(
            html,
            "div#UCAP-CONTENT, div.pages_content, div.TRS_Editor, div.trs_editor_view",
        )
        if not content:
            return None

        # 文号
        doc_number = ""
        # 从正文前 500 字提取
        doc_number = extract_document_number(content[:500]) or ""
        # 从标题下方的 info 行提取
        if not doc_number:
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if re.search(r"[〔〔][^〕]+〔〕]", text):
                    doc_number = extract_document_number(text) or ""
                    if doc_number:
                        break

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

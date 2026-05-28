"""人社部爬虫（含 Tencent EdgeOne 反爬绕过）。"""

from __future__ import annotations
import logging
import re
import subprocess
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import Tag

from crawler.spiders.base import Spider
from crawler.parsers.date import parse_chinese_date
from crawler.parsers.document_number import extract_document_number
from crawler.parsers.content import extract_content

logger = logging.getLogger("crawler.mohrss")

# Tencent EdgeOne 反爬 JS 挑战识别特征
TENCENT_EO_SIGNATURE = "TencentEdgeOne"
CHALLENGE_THRESHOLD = 2000  # 小于此字节数视为反爬验证页


class MohrssSpider(Spider):
    """人力资源和社会保障部爬虫。"""

    def _fetch(self, url: str) -> str | None:
        """重写 _fetch，自动绕过 Tencent EdgeOne JS 挑战。"""
        self.rate_limiter.wait(self.source_id)
        ua = self.ua_pool.get()
        try:
            resp = self._session.get(
                url, headers={"User-Agent": ua}, timeout=self.timeout
            )
            resp.raise_for_status()
            # 检查是否为 Tencent EdgeOne 反爬挑战
            if len(resp.text) < CHALLENGE_THRESHOLD:
                solved = self._solve_challenge(url, resp.text)
                if solved:
                    return solved
                # 解救失败，降级返回原始内容（可能为空列表）
                return None
            resp.encoding = resp.apparent_encoding or "utf-8"
            return resp.text
        except requests.RequestException as e:
            logger.error("请求失败 %s: %s", url, e)
            return None

    def _solve_challenge(self, url: str, challenge_html: str) -> str | None:
        """通过 Node.js 执行 JS 挑战，获取有效 cookie 后重试。"""
        match = re.search(r"<script>(.*?)</script>", challenge_html, re.DOTALL)
        if not match:
            return None
        challenge_js = match.group(1)

        node_code = (
            """
var cookieJar = "";
global.document = {
    get cookie() { return cookieJar; },
    set cookie(val) {
        var name = val.split("=")[0];
        cookieJar = cookieJar.split(";").filter(function(c) { return c.trim() && !c.trim().startsWith(name+"="); }).join(";");
        if (cookieJar && !cookieJar.endsWith(";")) cookieJar += ";";
        cookieJar += val;
    }
};
global.setTimeout = function(fn, ms) { if (typeof fn === "function") fn(); };
"""
            + challenge_js
            + "\nconsole.log(cookieJar);"
        )

        try:
            result = subprocess.run(
                ["node", "-e", node_code],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning("Node.js 执行反爬 JS 失败: %s", e)
            return None

        cookies_str = result.stdout.strip()
        if not cookies_str:
            return None

        cookie_pairs = {}
        for part in cookies_str.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                cookie_pairs[k] = v.replace("#", "").strip()

        if not cookie_pairs:
            return None

        cookie_header = "; ".join(f"{k}={v}" for k, v in cookie_pairs.items())
        ua = self.ua_pool.get()
        try:
            resp = self._session.get(
                url,
                headers={"User-Agent": ua, "Cookie": cookie_header},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            if len(resp.text) >= CHALLENGE_THRESHOLD:
                logger.info("反爬 JS 挑战成功: %s", url)
                resp.encoding = resp.apparent_encoding or "utf-8"
                return resp.text
            else:
                logger.warning("反爬 JS 挑战后仍被拦截: %s", url)
                return None
        except requests.RequestException as e:
            logger.error("挑战重试请求失败 %s: %s", url, e)
            return None

    def parse_list(self, html: str, list_config: dict[str, Any]) -> list[dict[str, str]]:
        """解析列表页，支持 rsb_con_rightUl 和通用 li a 结构。"""
        soup = self._soup(html)
        base_url = self.config.get("list_page_base", list_config.get("url", self.config["base_url"]))
        entries: list[dict[str, str]] = []
        selector = list_config.get("list_selector", "ul.rsb_con_rightUl li a")
        for a in soup.select(selector):
            if not isinstance(a, Tag):
                continue
            href = a.get("href", "")
            title = a.get_text(strip=True)
            if not href or not title:
                continue
            full_url = urljoin(base_url, href)
            # 尝试提取同行 span 中的日期
            parent_li = a.find_parent("li")
            publish_date = ""
            if parent_li:
                date_span = parent_li.find("span")
                if date_span:
                    publish_date = parse_chinese_date(date_span.get_text(strip=True)) or ""
            entries.append({"title": title, "url": full_url, "publishDate": publish_date})
        return entries

    def parse_detail(self, html: str, base_url: str) -> dict[str, Any] | None:
        soup = self._soup(html)

        # 标题：取 <title> 标签，去掉末尾站点名
        title = ""
        title_el = soup.select_one("title")
        if title_el:
            raw = title_el.get_text(strip=True)
            # 去掉末尾的 _XXX 站点名
            for sep in ["_", "-", "——"]:
                if sep in raw:
                    raw = raw.rsplit(sep, 1)[0].strip()
            title = raw
        if not title:
            title_el = soup.select_one("h1, h2")
            if title_el:
                title = title_el.get_text(strip=True)
        if not title:
            return None

        # 发布日期：优先 meta[pubdate]
        publish_date = ""
        meta = soup.select_one("meta[name='pubdate'], meta[name='PubDate']")
        if meta and meta.get("content"):
            publish_date = parse_chinese_date(meta["content"])
        if not publish_date:
            for sel in ["div.gknrwz", "div.content-info span.date"]:
                el = soup.select_one(sel)
                if el:
                    publish_date = parse_chinese_date(el.get_text(strip=True))
                    if publish_date:
                        break

        # 正文
        content = extract_content(html, "div.TRS_Editor, div.content-body, div.article-content")
        if not content:
            return None

        # 文号
        doc_number = ""
        for sel in ["div.gknrwz", "div.content-info", "div.article-info"]:
            el = soup.select_one(sel)
            if el:
                doc_number = extract_document_number(el.get_text(strip=True)) or ""
                if doc_number:
                    break

        # 生成 ID
        import hashlib
        raw = f"{base_url}_{publish_date or ''}"
        policy_id = f"mohrss-{hashlib.md5(raw.encode()).hexdigest()[:8]}"

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
            "issuingAuthority": "人力资源和社会保障部",
            "status": "effective",
            "summary": content[:200] if len(content) > 200 else content,
            "content": content,
            "contentHtml": None,
        }

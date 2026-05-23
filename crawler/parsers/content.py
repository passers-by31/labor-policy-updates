"""正文内容提取。"""

import re
from bs4 import BeautifulSoup, Tag


def extract_content(html: str, selector: str | None = None) -> str:
    """从 HTML 中提取正文内容。"""
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    if selector:
        elem = soup.select_one(selector)
        if elem:
            return _clean_text(elem.get_text(separator="\n", strip=True))
    # 后备：尝试常见的正文容器
    for fallback in [
        "div.TRS_Editor", "div.content", "div.article-content",
        "div.content-body", "div#UCAP-CONTENT", "article", ".main-content",
    ]:
        elem = soup.select_one(fallback)
        if elem:
            return _clean_text(elem.get_text(separator="\n", strip=True))
    # 最后后备：取 body 文本
    body = soup.find("body")
    if body:
        return _clean_text(body.get_text(separator="\n", strip=True))
    return _clean_text(soup.get_text(separator="\n", strip=True))


def _clean_text(text: str) -> str:
    """清理文本：多余空白、空行。"""
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\n\s*\n", "\n", text)
    return text.strip()

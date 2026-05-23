"""中文日期解析。"""

import re
from datetime import datetime

DATE_PATTERNS = [
    (r"(\d{4})年(\d{1,2})月(\d{1,2})日", "%Y-%m-%d"),
    (r"(\d{4})-(\d{1,2})-(\d{1,2})", "%Y-%m-%d"),
    (r"(\d{4})/(\d{1,2})/(\d{1,2})", "%Y-%m-%d"),
    (r"(\d{4})\.(\d{1,2})\.(\d{1,2})", "%Y-%m-%d"),
    (r"(\d{4})年(\d{1,2})月", "%Y-%m"),
]


def parse_chinese_date(text: str) -> str | None:
    """从文本中解析日期，返回 YYYY-MM-DD 格式。"""
    if not text:
        return None
    for pattern, fmt in DATE_PATTERNS:
        match = re.search(pattern, text)
        if match:
            try:
                dt = datetime.strptime(match.group(0), fmt.replace("%Y-%m-%d", "%Y年%m月%d日")
                                       if "年" in pattern else fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                try:
                    groups = match.groups()
                    y, m, d = int(groups[0]), int(groups[1]), int(groups[2]) if len(groups) > 2 else 1
                    return f"{y:04d}-{m:02d}-{d:02d}"
                except (ValueError, IndexError):
                    continue
    return None


def parse_full_datetime(text: str) -> str | None:
    """从文本中解析完整日期时间，返回 YYYY-MM-DD 格式（丢弃具体时间）。"""
    return parse_chinese_date(text)

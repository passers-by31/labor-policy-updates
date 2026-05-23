"""政策数据校验工具。"""

import re
from typing import Any

REQUIRED_FIELDS = ["id", "title", "publishDate", "content", "url"]
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_policy(policy: dict[str, Any]) -> tuple[bool, list[str]]:
    """验证政策对象是否合法。返回 (是否合法, 错误信息列表)。"""
    errors: list[str] = []
    for field in REQUIRED_FIELDS:
        if field not in policy or not policy.get(field):
            errors.append(f"缺少必填字段: {field}")
    if "publishDate" in policy and policy["publishDate"]:
        if not DATE_PATTERN.match(str(policy["publishDate"])):
            errors.append(f"日期格式无效: {policy['publishDate']}，应为 YYYY-MM-DD")
    if "url" in policy and policy["url"]:
        url = str(policy["url"])
        if not url.startswith(("http://", "https://")):
            errors.append(f"URL 格式无效: {url}")
    return len(errors) == 0, errors

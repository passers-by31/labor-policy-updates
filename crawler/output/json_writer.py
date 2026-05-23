"""JSON 输出：合并去重后写入 policies.json 和 changelog.json。"""

import json
import os
from datetime import date, datetime
from typing import Any

from crawler.filters.dedup import Deduplicator


def load_existing_policies(output_dir: str) -> list[dict[str, Any]]:
    """加载现有的 policies.json。"""
    path = os.path.join(output_dir, "policies.json")
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def merge_and_write(
    new_policies: list[dict[str, Any]],
    output_dir: str,
) -> dict[str, Any]:
    """合并新政策并写入文件。返回 changelog 条目。"""
    existing = load_existing_policies(output_dir)
    dedup = Deduplicator(existing)

    truly_new: list[dict[str, Any]] = []
    now = date.today()
    today_str = now.isoformat()

    for policy in new_policies:
        url = policy.get("url", "")
        doc_num = policy.get("documentNumber", "")
        if not dedup.is_duplicate(url, doc_num):
            policy["crawlDate"] = datetime.now().isoformat()
            policy["isNew"] = True
            truly_new.append(policy)
            dedup.add(url, doc_num, policy.get("id"))

    if not truly_new:
        return {
            "date": today_str,
            "timestamp": datetime.now().isoformat(),
            "newCount": 0,
            "updatedCount": 0,
            "totalCount": len(existing),
            "newPolicies": [],
            "summary": "无新增政策",
        }

    # 合并：新政策在前，按发布时间降序
    merged = truly_new + existing
    merged.sort(key=lambda p: p.get("publishDate", ""), reverse=True)

    _write_json(output_dir, "policies.json", merged)

    changelog_entry: dict[str, Any] = {
        "date": today_str,
        "timestamp": datetime.now().isoformat(),
        "newCount": len(truly_new),
        "updatedCount": 0,
        "totalCount": len(merged),
        "newPolicies": [p["id"] for p in truly_new],
        "summary": f"新增 {len(truly_new)} 条政策",
    }

    # 更新 changelog
    changelog_path = os.path.join(output_dir, "changelog.json")
    changelog: list[dict[str, Any]] = []
    if os.path.exists(changelog_path):
        with open(changelog_path, "r", encoding="utf-8") as f:
            changelog = json.load(f)
    changelog.insert(0, changelog_entry)
    changelog = changelog[:365]  # 保留最近一年
    _write_json(output_dir, "changelog.json", changelog)

    return changelog_entry


def _write_json(output_dir: str, filename: str, data: Any) -> None:
    """写入 JSON 文件（确保目录存在）。"""
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

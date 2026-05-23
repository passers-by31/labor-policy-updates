"""历史数据归档：按月拆分。"""

import json
import os
import shutil
from datetime import datetime
from typing import Any


def archive_policies(policies: list[dict[str, Any]], output_dir: str) -> None:
    """按月归档历史政策数据。"""
    archive_dir = os.path.join(output_dir, "archive")
    os.makedirs(archive_dir, exist_ok=True)

    monthly: dict[str, list[dict[str, Any]]] = {}
    for p in policies:
        pub = p.get("publishDate", "")
        month_key = pub[:7] if pub else "unknown"
        monthly.setdefault(month_key, []).append(p)

    for month, items in monthly.items():
        path = os.path.join(archive_dir, f"policies-{month}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)

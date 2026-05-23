"""相关性过滤器。"""

from __future__ import annotations
from typing import Any

import yaml
import os


class RelevanceFilter:
    """基于关键词评分的相关性过滤器。"""

    def __init__(self, config_path: str | None = None):
        self.include: list[str] = []
        self.exclude: list[str] = []
        self.weights: dict[str, int] = {}
        self.threshold = 2
        if config_path and os.path.exists(config_path):
            self._load_config(config_path)

    def _load_config(self, path: str) -> None:
        with open(path, "r", encoding="utf-8") as f:
            cfg: dict[str, Any] = yaml.safe_load(f)
        self.include = [kw.lower() for kw in cfg.get("include", [])]
        self.exclude = [kw.lower() for kw in cfg.get("exclude", [])]
        weights = cfg.get("weights", {})
        self.weights = {
            "title": weights.get("title_hit", 3),
            "tag": weights.get("tag_hit", 2),
            "summary": weights.get("summary_hit", 1),
            "content": weights.get("content_hit", 1),
            "content_first": weights.get("content_first_paragraph_hit", 1),
        }
        self.threshold = weights.get("threshold", 2)

    def is_relevant(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
    ) -> tuple[bool, int]:
        """判断内容是否与劳动政策相关。返回 (是否相关, 评分)。"""
        title_lower = title.lower()
        content_lower = content.lower()
        tags_lower = [t.lower() for t in (tags or [])]
        first_para = content_lower.split("\n")[0] if content_lower else ""

        # 排除检查：命中任一排除词即丢弃（仅在标题中检查，避免正文误杀）
        for kw in self.exclude:
            if kw in title_lower:
                return False, 0

        score = 0
        for kw in self.include:
            if kw in title_lower:
                score += self.weights.get("title", 3)
            if any(kw in t for t in tags_lower):
                score += self.weights.get("tag", 2)
            if kw in first_para:
                score += self.weights.get("content_first", 1)
            if kw in content_lower:
                score += self.weights.get("content", 1)

        return score >= self.threshold, score

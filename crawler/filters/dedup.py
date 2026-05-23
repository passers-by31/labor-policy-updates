"""URL 和文号双重去重器。"""

import json
import hashlib
from typing import Any


class Deduplicator:
    """去重器：URL 哈希 + 文号去重。"""

    def __init__(self, existing_policies: list[dict[str, Any]] | None = None):
        self._url_hashes: set[str] = set()
        self._doc_numbers: set[str] = set()
        self._id_set: set[str] = set()
        if existing_policies:
            for p in existing_policies:
                url = p.get("url", "")
                if url:
                    self._url_hashes.add(self._hash_url(url))
                doc_num = p.get("documentNumber", "")
                if doc_num:
                    self._doc_numbers.add(doc_num)
                pid = p.get("id", "")
                if pid:
                    self._id_set.add(pid)

    @staticmethod
    def _hash_url(url: str) -> str:
        return hashlib.md5(url.strip().rstrip("/").encode("utf-8")).hexdigest()

    def is_duplicate(self, url: str, doc_number: str | None = None) -> bool:
        """检查是否重复。"""
        url_hash = self._hash_url(url)
        if url_hash in self._url_hashes:
            return True
        if doc_number and doc_number in self._doc_numbers:
            return True
        return False

    def add(self, url: str, doc_number: str | None = None, policy_id: str | None = None) -> None:
        """将条目加入去重集合。"""
        self._url_hashes.add(self._hash_url(url))
        if doc_number:
            self._doc_numbers.add(doc_number)
        if policy_id:
            self._id_set.add(policy_id)

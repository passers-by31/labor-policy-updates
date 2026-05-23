"""文号提取与规范化。"""

import re

DOC_NUMBER_PATTERNS = [
    re.compile(r"([一-龥]+(?:发|函|字|办|厅|组))?〔?(\d{4})〕?(\d+)(?:号)?(?:[一-龥]*号?)?"),
    re.compile(r"([一-龥]+)\[(\d{4})\](\d+)(?:号)?"),
]


def extract_document_number(text: str) -> str | None:
    """从文本中提取文号。"""
    if not text:
        return None
    for pattern in DOC_NUMBER_PATTERNS:
        match = pattern.search(text)
        if match:
            groups = match.groups()
            if groups[0] and groups[1] and groups[2]:
                return f"{groups[0]}〔{groups[1]}〕{groups[2]}号"
            elif groups[1] and groups[2]:
                return f"〔{groups[1]}〕{groups[2]}号"
    return None

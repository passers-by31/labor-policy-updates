"""编码检测与转换工具。"""

import chardet


def detect_encoding(content: bytes) -> str:
    """检测字节内容的编码。"""
    if not content:
        return "utf-8"
    result = chardet.detect(content)
    return result.get("encoding", "utf-8")


def to_utf8(content: bytes, original_encoding: str | None = None) -> str:
    """将字节内容转换为 UTF-8 字符串。"""
    if isinstance(content, str):
        return content
    if original_encoding:
        try:
            return content.decode(original_encoding)
        except (UnicodeDecodeError, LookupError):
            pass
    detected = detect_encoding(content)
    encoding = detected if detected else "utf-8"
    try:
        return content.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        return content.decode("utf-8", errors="replace")

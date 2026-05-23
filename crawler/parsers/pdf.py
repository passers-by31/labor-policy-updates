"""PDF 文本提取。"""

import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str | None:
    """从 PDF 文件中提取文本。扫描件返回 None。"""
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber 未安装，无法解析 PDF")
        return None
    try:
        with pdfplumber.open(pdf_path) as pdf:
            pages_text = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages_text.append(text.strip())
            if not pages_text:
                logger.info("PDF 无文本层（可能为扫描件）: %s", pdf_path)
                return None
            return "\n".join(pages_text)
    except Exception as e:
        logger.error("PDF 解析失败 %s: %s", pdf_path, e)
        return None

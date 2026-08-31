"""OCR —— 扫描件/图片文字识别

引擎优先级：RapidOCR（轻量）→ PaddleOCR（重武器）→ 无（跳过并告警）
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ocr")

_engine: Optional[object] = None
_engine_name: str = ""


def _load_engine():
    """懒加载 OCR 引擎"""
    global _engine, _engine_name
    if _engine is not None:
        return _engine, _engine_name

    try:
        from rapidocr_onnxruntime import RapidOCR  # type: ignore

        _engine = RapidOCR()
        _engine_name = "rapidocr"
        logger.info("OCR 引擎: RapidOCR")
        return _engine, _engine_name
    except Exception as e:  # noqa: BLE001
        logger.debug("rapidocr 不可用: %s", e)

    try:
        from paddleocr import PaddleOCR  # type: ignore

        _engine = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
        _engine_name = "paddle"
        logger.info("OCR 引擎: PaddleOCR")
        return _engine, _engine_name
    except Exception as e:  # noqa: BLE001
        logger.debug("paddleocr 不可用: %s", e)

    return None, ""


def ocr_image(image_path) -> str:
    """识别图片中的文字，返回文本；无引擎时返回空串"""
    path = Path(image_path)
    engine, name = _load_engine()
    if engine is None:
        logger.warning("未安装 OCR 引擎（rapidocr/paddleocr），跳过图片识别: %s", path)
        return ""

    try:
        import numpy as np
        from PIL import Image

        img = np.array(Image.open(path).convert("RGB"))
        if name == "rapidocr":
            result, _ = engine(img)
            if not result:
                return ""
            return "\n".join(str(item[1]) for item in result)
        if name == "paddle":
            result = engine.ocr(img, cls=True)
            lines: list[str] = []
            for page in result or []:
                for line in page or []:
                    lines.append(str(line[1][0]))
            return "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        logger.warning("OCR 识别失败 %s: %s", path, e)
    return ""


def ocr_pdf_pages(pdf_path, pages=None) -> dict[int, str]:
    """把 PDF 指定页渲染成图片后 OCR（扫描件场景）

    Args:
        pdf_path: PDF 文件路径
        pages: 页号列表（1 起）；None 表示全部页
    Returns:
        {页码: 识别文本}
    """
    try:
        import fitz  # PyMuPDF
    except Exception as e:  # noqa: BLE001
        logger.warning("PyMuPDF 不可用，无法渲染扫描页: %s", e)
        return {}

    doc = fitz.open(str(pdf_path))
    out: dict[int, str] = {}
    page_nums = pages or list(range(1, doc.page_count + 1))
    for pno in page_nums:
        if pno < 1 or pno > doc.page_count:
            continue
        page = doc[pno - 1]
        pix = page.get_pixmap(dpi=200)
        tmp = Path(pdf_path).with_suffix(f"._p{pno}.png")
        pix.save(str(tmp))
        try:
            text = ocr_image(tmp)
            if text.strip():
                out[pno] = text
        finally:
            tmp.unlink(missing_ok=True)
    doc.close()
    return out

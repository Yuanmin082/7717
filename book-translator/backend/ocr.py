"""扫描版 PDF 的 OCR 支持。

对没有内嵌文字（纯图片扫描）的页面，渲染成图片后用 Tesseract 识别英文文字。
需要系统安装 tesseract-ocr，以及 pip 包 pytesseract。
"""
import re

import fitz

try:
    import pytesseract
    from PIL import Image
    _PIL_OK = True
except ImportError:
    _PIL_OK = False


def tesseract_available() -> bool:
    if not _PIL_OK:
        return False
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001
        return False


def ocr_status() -> dict:
    ok = tesseract_available()
    detail = ""
    if not _PIL_OK:
        detail = "未安装 pytesseract / Pillow"
    elif not ok:
        detail = "未检测到 tesseract 程序，请安装 tesseract-ocr"
    return {"available": ok, "detail": detail}


def _paragraphs_from_text(text: str) -> list:
    """把 OCR 出的纯文本切成段落块。"""
    blocks = []
    # 以空行为段落分隔
    chunks = re.split(r"\n\s*\n", text)
    for chunk in chunks:
        lines = [ln.strip() for ln in chunk.splitlines() if ln.strip()]
        if not lines:
            continue
        merged = ""
        for ln in lines:
            if merged.endswith("-") and re.search(r"[A-Za-z]-$", merged):
                merged = merged[:-1] + ln
            elif merged:
                merged += " " + ln
            else:
                merged = ln
        merged = merged.strip()
        if not merged:
            continue
        btype = "h" if (len(merged) < 80 and merged.isupper()) else "p"
        blocks.append({"type": btype, "text": merged})
    return blocks


def ocr_page(page: "fitz.Page", lang: str = "eng", dpi: int = 300) -> list:
    """对单个 PDF 页做 OCR，返回段落块列表。"""
    if not tesseract_available():
        return []
    zoom = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    text = pytesseract.image_to_string(img, lang=lang)
    return _paragraphs_from_text(text)

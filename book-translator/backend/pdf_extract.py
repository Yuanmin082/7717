"""PDF 文本抽取：按页输出段落级文本块，尽量还原阅读顺序并合并断行。

对扫描版（无内嵌文字）的页面，可按 ocr_mode 调用 OCR 识别。
"""
import re
import fitz  # PyMuPDF

from . import ocr

# 一页内嵌文字少于该字符数时，认为可能是扫描页，auto 模式下尝试 OCR
OCR_TEXT_THRESHOLD = 20


def _clean_block(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines()]
    out = ""
    for ln in lines:
        if not ln:
            continue
        if out.endswith("-") and re.search(r"[A-Za-z]-$", out):
            # 行尾连字符断词，直接拼接
            out = out[:-1] + ln
        elif out:
            out += " " + ln
        else:
            out = ln
    return out.strip()


def _looks_like_heading(text: str, size: float, body_size: float) -> bool:
    if len(text) > 120:
        return False
    if size and body_size and size >= body_size * 1.25:
        return True
    # 全大写短行、或章节编号
    if len(text) < 80 and (text.isupper() or re.match(r"^(chapter|part|section)\b", text, re.I)):
        return True
    return False


def extract_pages(pdf_path: str, ocr_mode: str = "auto", progress=None) -> list:
    """返回 (pages, title)。

    ocr_mode: "off" 从不 OCR；"auto" 仅对内嵌文字极少的页面 OCR；"force" 全部 OCR。
    progress: 可选回调 progress(done, total)。
    """
    doc = fitz.open(pdf_path)
    pages = []
    ocr_ready = ocr_mode != "off" and ocr.tesseract_available()
    try:
        # 估计正文字号（用中位数）
        sizes = []
        for page in doc:
            d = page.get_text("dict")
            for blk in d.get("blocks", []):
                for line in blk.get("lines", []):
                    for span in line.get("spans", []):
                        if span.get("text", "").strip():
                            sizes.append(round(span.get("size", 0), 1))
        body_size = 0.0
        if sizes:
            sizes.sort()
            body_size = sizes[len(sizes) // 2]

        total = doc.page_count
        for pno, page in enumerate(doc):
            blocks_out = []
            d = page.get_text("dict")
            raw_blocks = []
            for blk in d.get("blocks", []):
                if blk.get("type", 0) != 0:  # 跳过图片块
                    continue
                spans_text = []
                max_size = 0.0
                for line in blk.get("lines", []):
                    line_text = "".join(s.get("text", "") for s in line.get("spans", []))
                    spans_text.append(line_text)
                    for s in line.get("spans", []):
                        max_size = max(max_size, s.get("size", 0))
                text = _clean_block("\n".join(spans_text))
                if not text:
                    continue
                bbox = blk.get("bbox", [0, 0, 0, 0])
                raw_blocks.append((bbox[1], bbox[0], text, max_size))
            # 按 y 再按 x 排序，恢复阅读顺序
            raw_blocks.sort(key=lambda b: (round(b[0]), round(b[1])))
            for _, _, text, size in raw_blocks:
                btype = "h" if _looks_like_heading(text, size, body_size) else "p"
                blocks_out.append({"type": btype, "text": text})

            # 扫描页 OCR 兜底
            embedded_chars = sum(len(b["text"]) for b in blocks_out)
            need_ocr = ocr_ready and (
                ocr_mode == "force" or
                (ocr_mode == "auto" and embedded_chars < OCR_TEXT_THRESHOLD)
            )
            if need_ocr:
                ocr_blocks = ocr.ocr_page(page)
                if ocr_blocks:
                    blocks_out = ocr_blocks

            pages.append(blocks_out)
            if progress:
                progress(pno + 1, total)
        title = doc.metadata.get("title") if doc.metadata else None
        return pages, (title or "")
    finally:
        doc.close()

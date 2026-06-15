"""导出：双语对照 HTML / Markdown / Word(docx)。"""
import html
import io
import re

from . import storage


def _esc(t: str) -> str:
    return html.escape(t or "")


def export_html(book_id: int) -> bytes:
    data = storage.book_full(book_id)
    if not data:
        return b""
    book = data["book"]
    parts = [
        "<!DOCTYPE html><html lang='zh'><head><meta charset='utf-8'>",
        f"<title>{_esc(book['title'])} · 双语对照</title>",
        """<style>
        body{font-family:-apple-system,'Segoe UI','Microsoft YaHei',sans-serif;max-width:1100px;
        margin:0 auto;padding:24px;color:#222;line-height:1.7}
        h1{text-align:center}
        .page{border-top:2px dashed #ddd;margin-top:32px;padding-top:12px}
        .pn{color:#999;font-size:13px}
        .row{display:flex;gap:24px;margin:10px 0}
        .col{flex:1}
        .en{color:#555}
        .zh{color:#111}
        .h .en,.h .zh{font-weight:700;font-size:1.15em}
        .note{background:#fff8e6;border-left:4px solid #f0b400;padding:10px 14px;margin:12px 0;
        border-radius:4px;font-size:14px;white-space:pre-wrap}
        .unote{background:#eef6ff;border-left:4px solid #3b82f6;padding:10px 14px;border-radius:4px;font-size:14px;white-space:pre-wrap}
        </style></head><body>""",
        f"<h1>{_esc(book['title'])}</h1>",
        "<p style='text-align:center;color:#999'>英中双语对照 · 由 Book Translator 生成</p>",
    ]
    for page in sorted(data["blocks_by_page"].keys()):
        parts.append(f"<div class='page'><div class='pn'>第 {page} 页</div>")
        for b in data["blocks_by_page"][page]:
            cls = "row h" if b["type"] == "h" else "row"
            parts.append(
                f"<div class='{cls}'><div class='col en'>{_esc(b['original'])}</div>"
                f"<div class='col zh'>{_esc(b['translation'])}</div></div>"
            )
        note = data["notes"].get(page, {})
        if note.get("ai_note"):
            parts.append(f"<div class='note'><b>AI 笔记</b><br>{_esc(note['ai_note'])}</div>")
        if note.get("user_note"):
            parts.append(f"<div class='unote'><b>我的笔记</b><br>{_esc(note['user_note'])}</div>")
        parts.append("</div>")
    parts.append("</body></html>")
    return "\n".join(parts).encode("utf-8")


def export_markdown(book_id: int) -> bytes:
    data = storage.book_full(book_id)
    if not data:
        return b""
    book = data["book"]
    out = [f"# {book['title']}\n", "> 英中双语对照 · 由 Book Translator 生成\n"]
    for page in sorted(data["blocks_by_page"].keys()):
        out.append(f"\n---\n\n### 第 {page} 页\n")
        for b in data["blocks_by_page"][page]:
            prefix = "#### " if b["type"] == "h" else ""
            out.append(f"{prefix}{b['original']}\n")
            out.append(f"{prefix}**{b['translation']}**\n")
        note = data["notes"].get(page, {})
        if note.get("ai_note"):
            out.append(f"\n> 📝 **AI 笔记**\n>\n> {note['ai_note'].replace(chr(10), chr(10)+'> ')}\n")
        if note.get("user_note"):
            out.append(f"\n> ✍️ **我的笔记**\n>\n> {note['user_note'].replace(chr(10), chr(10)+'> ')}\n")
    return "\n".join(out).encode("utf-8")


def export_docx(book_id: int) -> bytes:
    from docx import Document
    from docx.shared import Pt, RGBColor

    data = storage.book_full(book_id)
    if not data:
        return b""
    book = data["book"]
    doc = Document()
    doc.add_heading(book["title"] or "双语对照", level=0)
    for page in sorted(data["blocks_by_page"].keys()):
        doc.add_paragraph(f"第 {page} 页").italic = True
        for b in data["blocks_by_page"][page]:
            if b["type"] == "h":
                doc.add_heading(b["original"], level=2)
                doc.add_heading(b["translation"], level=2)
            else:
                p = doc.add_paragraph()
                r = p.add_run(b["original"])
                r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
                r.font.size = Pt(10)
                doc.add_paragraph(b["translation"])
        note = data["notes"].get(page, {})
        if note.get("ai_note"):
            p = doc.add_paragraph()
            p.add_run("【AI 笔记】" + note["ai_note"]).italic = True
        if note.get("user_note"):
            p = doc.add_paragraph()
            p.add_run("【我的笔记】" + note["user_note"]).italic = True
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def safe_filename(name: str) -> str:
    name = re.sub(r"[^\w一-龥\-. ]", "_", name or "book").strip()
    return name or "book"

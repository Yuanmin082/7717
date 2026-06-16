"""Flask 服务：提供前端页面与 REST 接口。桌面版与浏览器版共用。"""
import os
import sys
import tempfile

from flask import Flask, jsonify, request, send_file, send_from_directory

from . import config, export, jobs, ocr, pdf_extract, storage, translator


def _frontend_dir() -> str:
    # PyInstaller 打包后资源解压到 sys._MEIPASS
    base = getattr(sys, "_MEIPASS", None)
    if base:
        cand = os.path.join(base, "frontend")
        if os.path.isdir(cand):
            return cand
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


FRONTEND_DIR = _frontend_dir()


def create_app() -> Flask:
    storage.init_db()
    app = Flask(__name__, static_folder=None)
    app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB PDF 上限

    # ---------- 静态页面 ----------
    @app.get("/")
    def index():
        return send_from_directory(FRONTEND_DIR, "index.html")

    @app.get("/<path:fname>")
    def static_files(fname):
        return send_from_directory(FRONTEND_DIR, fname)

    # ---------- 配置 ----------
    @app.get("/api/config")
    def get_config():
        return jsonify(config.public_config())

    @app.post("/api/config")
    def set_config():
        body = request.get_json(force=True) or {}
        # 空字符串的 api_key 不覆盖已有值
        if body.get("api_key") == "":
            body.pop("api_key", None)
        config.save_config(body)
        return jsonify(config.public_config())

    @app.get("/api/ocr-status")
    def ocr_status():
        return jsonify(ocr.ocr_status())

    @app.post("/api/test-connection")
    def test_conn():
        try:
            reply = translator.test_connection()
            return jsonify({"ok": True, "reply": reply})
        except Exception as e:  # noqa: BLE001
            return jsonify({"ok": False, "error": str(e)}), 400

    # ---------- 书库 ----------
    @app.get("/api/books")
    def books():
        return jsonify(storage.list_books())

    @app.post("/api/books/upload")
    def upload():
        if "file" not in request.files:
            return jsonify({"error": "未收到文件"}), 400
        f = request.files["file"]
        if not f.filename.lower().endswith(".pdf"):
            return jsonify({"error": "请上传 PDF 文件"}), 400
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        f.save(tmp.name)
        try:
            ocr_mode = config.load_config().get("ocr_mode", "auto")
            pages, meta_title = pdf_extract.extract_pages(tmp.name, ocr_mode=ocr_mode)
        except Exception as e:  # noqa: BLE001
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            return jsonify({"error": f"PDF 解析失败：{e}"}), 400
        if (meta_title or "").strip().lower() in ("", "untitled"):
            meta_title = ""
        title = meta_title or os.path.splitext(os.path.basename(f.filename))[0]
        book_id = storage.create_book(title, f.filename, pages)
        # 保存原始 PDF，供左侧显示原页
        try:
            storage.PDF_DIR.mkdir(parents=True, exist_ok=True)
            dest = str(storage.PDF_DIR / f"{book_id}.pdf")
            os.replace(tmp.name, dest)
            storage.set_pdf_path(book_id, dest)
        except OSError:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
        return jsonify(storage.get_book(book_id))

    @app.get("/api/books/<int:book_id>/page/<int:page>/image")
    def page_image(book_id, page):
        """把 PDF 第 page 页渲染成 PNG 返回（左侧原页显示）。"""
        b = storage.get_book(book_id)
        if not b or not b.get("pdf_path") or not os.path.exists(b["pdf_path"]):
            return jsonify({"error": "no_pdf"}), 404
        try:
            import fitz
            doc = fitz.open(b["pdf_path"])
            pg = doc[page - 1]
            pix = pg.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x 清晰度
            data = pix.tobytes("png")
            doc.close()
        except Exception as e:  # noqa: BLE001
            return jsonify({"error": str(e)}), 400
        import io
        return send_file(io.BytesIO(data), mimetype="image/png")

    @app.get("/api/books/<int:book_id>")
    def book_detail(book_id):
        b = storage.get_book(book_id)
        if not b:
            return jsonify({"error": "not found"}), 404
        return jsonify(b)

    @app.delete("/api/books/<int:book_id>")
    def del_book(book_id):
        storage.delete_book(book_id)
        return jsonify({"ok": True})

    @app.get("/api/books/<int:book_id>/page/<int:page>")
    def page_content(book_id, page):
        blocks = storage.get_page_blocks(book_id, page)
        meta = storage.get_page_meta(book_id, page) or {}
        return jsonify({"blocks": blocks, "meta": meta})

    # ---------- 翻译 ----------
    @app.post("/api/books/<int:book_id>/translate")
    def translate_book(book_id):
        b = storage.get_book(book_id)
        if not b:
            return jsonify({"error": "not found"}), 404
        body = request.get_json(silent=True) or {}
        start = body.get("start")
        end = body.get("end")
        total = b["total_pages"]
        if start and end:
            pages = list(range(max(1, start), min(total, end) + 1))
        else:
            # 只翻译尚未翻译的页
            pages = []
            for p in range(1, total + 1):
                meta = storage.get_page_meta(book_id, p)
                if not meta or not meta.get("translated"):
                    pages.append(p)
        if not pages:
            return jsonify({"error": "没有需要翻译的页面"}), 400
        job_id = jobs.start_translation(book_id, pages)
        return jsonify({"job_id": job_id, "pages": len(pages)})

    @app.get("/api/jobs/<job_id>")
    def job_status(job_id):
        j = jobs.get_job(job_id)
        if not j:
            return jsonify({"error": "not found"}), 404
        return jsonify(j)

    # ---------- 笔记 / 修正 ----------
    @app.post("/api/books/<int:book_id>/page/<int:page>/regenerate-note")
    def regenerate_note(book_id, page):
        blocks = storage.get_page_blocks(book_id, page)
        page_text = "\n\n".join(b["original"] for b in blocks if b.get("original"))
        try:
            note = translator.make_note(page_text)
        except Exception as e:  # noqa: BLE001
            return jsonify({"error": str(e)}), 400
        storage.save_ai_note(book_id, page, note)
        return jsonify({"ai_note": note})

    @app.post("/api/books/<int:book_id>/page/<int:page>/usernote")
    def save_usernote(book_id, page):
        body = request.get_json(force=True) or {}
        storage.save_user_note(book_id, page, body.get("user_note", ""))
        return jsonify({"ok": True})

    @app.post("/api/blocks/<int:block_id>")
    def edit_block(block_id):
        body = request.get_json(force=True) or {}
        storage.update_block(block_id, body.get("translation", ""))
        return jsonify({"ok": True})

    # ---------- 导出 ----------
    @app.get("/api/books/<int:book_id>/export")
    def export_book(book_id):
        fmt = request.args.get("format", "html")
        b = storage.get_book(book_id)
        if not b:
            return jsonify({"error": "not found"}), 404
        name = export.safe_filename(b["title"])
        if fmt == "pdf":
            data = export.export_pdf(book_id)
            return _download(data, f"{name}-双语.pdf", "application/pdf")
        if fmt == "md":
            data = export.export_markdown(book_id)
            return _download(data, f"{name}.md", "text/markdown")
        if fmt == "docx":
            data = export.export_docx(book_id)
            return _download(
                data, f"{name}.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        data = export.export_html(book_id)
        return _download(data, f"{name}.html", "text/html")

    return app


def _download(data: bytes, filename: str, mimetype: str):
    import io
    return send_file(
        io.BytesIO(data), mimetype=mimetype, as_attachment=True, download_name=filename
    )

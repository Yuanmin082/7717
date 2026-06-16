"""SQLite 存储层：书籍、文本块、翻译结果、笔记、翻译缓存。"""
import hashlib
import sqlite3
import threading
import time
from contextlib import contextmanager

from .config import DB_PATH, APP_DIR

_lock = threading.Lock()


def _connect() -> sqlite3.Connection:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def db():
    with _lock:
        conn = _connect()
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                filename TEXT,
                total_pages INTEGER DEFAULT 0,
                translated_pages INTEGER DEFAULT 0,
                created_at REAL
            );
            CREATE TABLE IF NOT EXISTS blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER,
                page INTEGER,
                idx INTEGER,
                type TEXT,
                original TEXT,
                translation TEXT,
                FOREIGN KEY(book_id) REFERENCES books(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS pages (
                book_id INTEGER,
                page INTEGER,
                ai_note TEXT,
                user_note TEXT,
                translated INTEGER DEFAULT 0,
                PRIMARY KEY (book_id, page)
            );
            CREATE TABLE IF NOT EXISTS cache (
                hash TEXT PRIMARY KEY,
                value TEXT,
                created_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_blocks_book_page ON blocks(book_id, page);
            """
        )


# ---------- 书籍 ----------

def create_book(title: str, filename: str, pages: list) -> int:
    """pages: [[{type, text}, ...], ...]  按页给出文本块。"""
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO books (title, filename, total_pages, created_at) VALUES (?,?,?,?)",
            (title, filename, len(pages), time.time()),
        )
        book_id = cur.lastrowid
        for p_idx, blocks in enumerate(pages, start=1):
            conn.execute(
                "INSERT INTO pages (book_id, page, ai_note, user_note, translated) VALUES (?,?,?,?,0)",
                (book_id, p_idx, "", ""),
            )
            for b_idx, b in enumerate(blocks):
                conn.execute(
                    "INSERT INTO blocks (book_id, page, idx, type, original, translation) "
                    "VALUES (?,?,?,?,?,?)",
                    (book_id, p_idx, b_idx, b.get("type", "p"), b.get("text", ""), ""),
                )
        return book_id


def list_books() -> list:
    with db() as conn:
        rows = conn.execute("SELECT * FROM books ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def get_book(book_id: int):
    with db() as conn:
        row = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        return dict(row) if row else None


def delete_book(book_id: int) -> None:
    with db() as conn:
        conn.execute("DELETE FROM blocks WHERE book_id=?", (book_id,))
        conn.execute("DELETE FROM pages WHERE book_id=?", (book_id,))
        conn.execute("DELETE FROM books WHERE id=?", (book_id,))


# ---------- 页 / 块 ----------

def get_page_blocks(book_id: int, page: int) -> list:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM blocks WHERE book_id=? AND page=? ORDER BY idx",
            (book_id, page),
        ).fetchall()
        return [dict(r) for r in rows]


def get_page_meta(book_id: int, page: int):
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM pages WHERE book_id=? AND page=?", (book_id, page)
        ).fetchone()
        return dict(row) if row else None


def save_block_translation(block_id: int, translation: str) -> None:
    with db() as conn:
        conn.execute("UPDATE blocks SET translation=? WHERE id=?", (translation, block_id))


def save_page_result(book_id: int, page: int, translations: dict, ai_note: str) -> None:
    """translations: {block_id: translation}"""
    with db() as conn:
        for bid, tr in translations.items():
            conn.execute("UPDATE blocks SET translation=? WHERE id=?", (tr, bid))
        conn.execute(
            "UPDATE pages SET ai_note=?, translated=1 WHERE book_id=? AND page=?",
            (ai_note, book_id, page),
        )
        done = conn.execute(
            "SELECT COUNT(*) FROM pages WHERE book_id=? AND translated=1", (book_id,)
        ).fetchone()[0]
        conn.execute("UPDATE books SET translated_pages=? WHERE id=?", (done, book_id))


def save_ai_note(book_id: int, page: int, ai_note: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE pages SET ai_note=? WHERE book_id=? AND page=?",
            (ai_note, book_id, page),
        )


def save_user_note(book_id: int, page: int, user_note: str) -> None:
    with db() as conn:
        conn.execute(
            "UPDATE pages SET user_note=? WHERE book_id=? AND page=?",
            (user_note, book_id, page),
        )


def update_block(block_id: int, translation: str) -> None:
    """用户手动修正译文。"""
    save_block_translation(block_id, translation)


def book_full(book_id: int) -> dict:
    """导出用：取整本书所有页的原文/译文/笔记。"""
    book = get_book(book_id)
    if not book:
        return {}
    with db() as conn:
        blocks = conn.execute(
            "SELECT * FROM blocks WHERE book_id=? ORDER BY page, idx", (book_id,)
        ).fetchall()
        pages = conn.execute(
            "SELECT * FROM pages WHERE book_id=? ORDER BY page", (book_id,)
        ).fetchall()
    by_page = {}
    for b in blocks:
        by_page.setdefault(b["page"], []).append(dict(b))
    note_by_page = {p["page"]: dict(p) for p in pages}
    return {"book": book, "blocks_by_page": by_page, "notes": note_by_page}


# ---------- 翻译缓存 ----------

def cache_key(text: str, model: str, kind: str) -> str:
    return hashlib.sha256(f"{kind}|{model}|{text}".encode("utf-8")).hexdigest()


def cache_get(key: str):
    with db() as conn:
        row = conn.execute("SELECT value FROM cache WHERE hash=?", (key,)).fetchone()
        return row["value"] if row else None


def cache_set(key: str, value: str) -> None:
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cache (hash, value, created_at) VALUES (?,?,?)",
            (key, value, time.time()),
        )

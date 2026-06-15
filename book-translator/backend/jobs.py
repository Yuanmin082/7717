"""后台翻译任务：多页并发翻译并上报进度。"""
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import storage, translator
from .config import load_config

_jobs = {}
_jobs_lock = threading.Lock()


def get_job(job_id: str):
    with _jobs_lock:
        j = _jobs.get(job_id)
        return dict(j) if j else None


def _set(job_id: str, **kw):
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(kw)


def _translate_one_page(book_id: int, page: int):
    blocks = storage.get_page_blocks(book_id, page)
    translations = translator.translate_blocks(blocks)
    page_text = "\n\n".join(b["original"] for b in blocks if b.get("original"))
    note = translator.make_note(page_text)
    storage.save_page_result(book_id, page, translations, note)


def _run(job_id: str, book_id: int, pages: list):
    cfg = load_config()
    workers = max(1, min(int(cfg.get("concurrency", 4)), 8))
    _set(job_id, status="running", total=len(pages), done=0, error="")
    try:
        # 先用一页验证连通性，避免并发时一次性报错刷屏
        if pages:
            _translate_one_page(book_id, pages[0])
            _set(job_id, done=1)
            rest = pages[1:]
        else:
            rest = []
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futures = {ex.submit(_translate_one_page, book_id, p): p for p in rest}
            done = 1
            for fut in as_completed(futures):
                fut.result()  # 抛出异常则中止
                done += 1
                _set(job_id, done=done)
        _set(job_id, status="done", finished_at=time.time())
    except Exception as e:  # noqa: BLE001 - 汇总给前端展示
        _set(job_id, status="error", error=str(e))


def start_translation(book_id: int, pages: list) -> str:
    job_id = uuid.uuid4().hex[:12]
    with _jobs_lock:
        _jobs[job_id] = {
            "id": job_id,
            "book_id": book_id,
            "status": "pending",
            "total": len(pages),
            "done": 0,
            "error": "",
        }
    t = threading.Thread(target=_run, args=(job_id, book_id, pages), daemon=True)
    t.start()
    return job_id

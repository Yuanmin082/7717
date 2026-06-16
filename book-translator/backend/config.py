"""用户配置管理。

配置（含 DeepSeek API Key）保存在用户主目录下的 ~/.book-translator/config.json，
不会写进项目仓库，避免泄露密钥。
"""
import json
import os
from pathlib import Path

APP_DIR = Path(os.environ.get("BOOK_TRANSLATOR_HOME", Path.home() / ".book-translator"))
CONFIG_PATH = APP_DIR / "config.json"
DB_PATH = APP_DIR / "library.db"

DEFAULTS = {
    # 大模型接入（DeepSeek 默认，兼容 OpenAI 接口；也可填 Claude 兼容网关）
    "provider": "deepseek",
    "api_key": "",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat",
    # 翻译设置
    "target_lang": "中文",
    "concurrency": 4,          # 同时翻译的页数
    "temperature": 0.3,
    "make_notes": True,         # 是否生成 AI 笔记
    "note_style": "延伸思考",   # 笔记风格：延伸思考 / 精简版 / 讲解版 / 学术版
    "ocr_mode": "auto",         # 扫描页 OCR：off / auto / force
    "proxy": "",                # 代理地址，留空=不走代理直连；填如 http://127.0.0.1:7890
}


def _ensure_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    _ensure_dir()
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(updates: dict) -> dict:
    cfg = load_config()
    # 只接受已知字段，避免脏数据
    for key in DEFAULTS:
        if key in updates:
            cfg[key] = updates[key]
    _ensure_dir()
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    return cfg


def public_config() -> dict:
    """返回给前端的配置：隐藏 API Key 真实值，只告知是否已设置。"""
    cfg = load_config()
    safe = dict(cfg)
    key = cfg.get("api_key") or ""
    safe["api_key"] = ""
    safe["api_key_set"] = bool(key)
    safe["api_key_hint"] = (key[:4] + "…" + key[-4:]) if len(key) >= 8 else ("已设置" if key else "")
    return safe

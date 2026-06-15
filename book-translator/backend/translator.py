"""调用大模型（DeepSeek，兼容 OpenAI 接口）完成翻译与 AI 笔记生成。"""
import json
import re

import requests

from . import storage
from .config import load_config


class LLMError(Exception):
    pass


def _chat(messages: list, json_mode: bool = False, max_tokens: int = 4096) -> str:
    cfg = load_config()
    api_key = cfg.get("api_key", "").strip()
    if not api_key:
        raise LLMError("尚未设置 API Key，请先在「设置」中填写 DeepSeek API Key。")
    base = cfg.get("base_url", "https://api.deepseek.com").rstrip("/")
    url = base + "/v1/chat/completions" if not base.endswith("/v1") else base + "/chat/completions"
    # 兼容直接给到 /chat/completions 的情况
    if base.endswith("/chat/completions"):
        url = base
    payload = {
        "model": cfg.get("model", "deepseek-chat"),
        "messages": messages,
        "temperature": float(cfg.get("temperature", 0.3)),
        "max_tokens": max_tokens,
        "stream": False,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=180,
        )
    except requests.RequestException as e:
        raise LLMError(f"网络请求失败：{e}")
    if resp.status_code != 200:
        raise LLMError(f"模型接口返回 {resp.status_code}：{resp.text[:300]}")
    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        raise LLMError(f"接口返回格式异常：{json.dumps(data)[:300]}")


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(json)?", "", text).rsplit("```", 1)[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise


# ---------- 翻译 ----------

def translate_blocks(blocks: list) -> dict:
    """blocks: storage 里的块记录列表。返回 {block_id: 译文}。整页一次请求，按编号对齐。"""
    cfg = load_config()
    model = cfg.get("model", "deepseek-chat")
    target = cfg.get("target_lang", "中文")
    result = {}
    pending = []  # (block, cache_key)

    for b in blocks:
        original = (b.get("original") or "").strip()
        if not original:
            result[b["id"]] = ""
            continue
        ck = storage.cache_key(original, model, "translate")
        cached = storage.cache_get(ck)
        if cached is not None:
            result[b["id"]] = cached
        else:
            pending.append((b, ck))

    if not pending:
        return result

    numbered = "\n".join(f"[{i}] {b['original']}" for i, (b, _) in enumerate(pending))
    sys = (
        f"你是一名专业的图书译者。把用户给出的英文段落逐条翻译成{target}，"
        "要求准确、通顺、符合中文表达习惯，保留专有名词，必要时意译。"
        "严格按输入的编号一一对应，不要合并或拆分条目，不要添加解释。"
        '只返回 JSON：{"translations": {"0": "译文", "1": "译文", ...}}。'
    )
    content = _chat(
        [{"role": "system", "content": sys}, {"role": "user", "content": numbered}],
        json_mode=True,
        max_tokens=8192,
    )
    data = _extract_json(content)
    trans = data.get("translations", data)

    for i, (b, ck) in enumerate(pending):
        key = str(i)
        tr = ""
        if isinstance(trans, dict):
            tr = trans.get(key) or trans.get(i) or ""
        elif isinstance(trans, list) and i < len(trans):
            tr = trans[i]
        tr = (tr or "").strip()
        if not tr:
            # 兜底：单条重译
            tr = _translate_single(b["original"], target)
        storage.cache_set(ck, tr)
        result[b["id"]] = tr
    return result


def _translate_single(text: str, target: str) -> str:
    out = _chat(
        [
            {"role": "system", "content": f"把下面的英文翻译成{target}，只返回译文。"},
            {"role": "user", "content": text},
        ],
        max_tokens=4096,
    )
    return out.strip()


# ---------- AI 笔记 ----------

NOTE_PROMPTS = {
    "讲解版": "结合内容写一段中文学习笔记：概括本页要点，解释难点与背景，挑出3-6个重点词汇/术语并给中文释义。条理清晰，用 Markdown。",
    "精简版": "用中文写3-5条精简笔记：一句话概括要点，列出关键术语及释义。简短克制。",
    "学术版": "以学术视角写中文笔记：梳理论点与逻辑结构，指出关键概念、引用与潜在争议，给出延伸思考。",
}


def make_note(page_text: str) -> str:
    cfg = load_config()
    if not cfg.get("make_notes", True):
        return ""
    text = (page_text or "").strip()
    if len(text) < 40:
        return ""
    model = cfg.get("model", "deepseek-chat")
    ck = storage.cache_key(text[:4000], model, "note:" + cfg.get("note_style", "讲解版"))
    cached = storage.cache_get(ck)
    if cached is not None:
        return cached
    style = NOTE_PROMPTS.get(cfg.get("note_style", "讲解版"), NOTE_PROMPTS["讲解版"])
    note = _chat(
        [
            {"role": "system", "content": "你是中文阅读辅导老师，擅长把英文原著讲清楚。" + style},
            {"role": "user", "content": text[:6000]},
        ],
        max_tokens=2048,
    ).strip()
    storage.cache_set(ck, note)
    return note


def test_connection() -> str:
    """测试 API 是否可用。"""
    out = _chat([{"role": "user", "content": "回复两个字：可用"}], max_tokens=20)
    return out.strip()

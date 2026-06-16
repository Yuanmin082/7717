"use strict";

const $ = (s) => document.querySelector(s);
const api = (p, opt) => fetch(p, opt).then(async (r) => {
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || ("HTTP " + r.status));
  return data;
});

let state = { book: null, page: 1, jobTimer: null, noteTimer: null };

/* ---------- 提示 ---------- */
function toast(msg, ms = 2200) {
  const t = $("#toast");
  t.textContent = msg;
  t.classList.remove("hidden");
  clearTimeout(t._t);
  t._t = setTimeout(() => t.classList.add("hidden"), ms);
}

/* ---------- 极简 Markdown 渲染（笔记用） ---------- */
function md(src) {
  if (!src) return "";
  const esc = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const lines = src.split("\n");
  let html = "", inList = false;
  for (let raw of lines) {
    let line = esc(raw);
    line = line.replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/`(.+?)`/g, "<code>$1</code>");
    const h = line.match(/^(#{1,4})\s+(.*)/);
    const li = line.match(/^[\-*]\s+(.*)/);
    if (h) { if (inList) { html += "</ul>"; inList = false; } html += `<h3>${h[2]}</h3>`; }
    else if (li) { if (!inList) { html += "<ul>"; inList = true; } html += `<li>${li[1]}</li>`; }
    else if (line.trim() === "") { if (inList) { html += "</ul>"; inList = false; } }
    else { if (inList) { html += "</ul>"; inList = false; } html += `<div>${line}</div>`; }
  }
  if (inList) html += "</ul>";
  return html;
}

/* ---------- 书库 ---------- */
async function loadLibrary() {
  const books = await api("/api/books");
  const list = $("#bookList");
  list.innerHTML = "";
  $("#emptyLib").classList.toggle("hidden", books.length > 0);
  for (const b of books) {
    const pct = b.total_pages ? Math.round((b.translated_pages / b.total_pages) * 100) : 0;
    const card = document.createElement("div");
    card.className = "book-card";
    card.innerHTML = `
      <h3>${escapeHtml(b.title || "未命名")}</h3>
      <div class="book-meta">${b.total_pages} 页 · 已译 ${b.translated_pages} 页 (${pct}%)</div>
      <div class="bar"><span style="width:${pct}%"></span></div>
      <div class="card-actions">
        <button class="primary open">打开</button>
        <button class="del">删除</button>
      </div>`;
    card.querySelector(".open").onclick = () => openBook(b.id);
    card.querySelector(".del").onclick = async () => {
      if (!confirm("确定删除这本书及其翻译？")) return;
      await api(`/api/books/${b.id}`, { method: "DELETE" });
      loadLibrary();
    };
    list.appendChild(card);
  }
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

/* ---------- 上传 ---------- */
async function uploadFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf")) return toast("请选择 PDF 文件");
  toast("正在解析 PDF…", 60000);
  const fd = new FormData();
  fd.append("file", file);
  try {
    const book = await api("/api/books/upload", { method: "POST", body: fd });
    toast("解析完成，已加入书库");
    await loadLibrary();
    openBook(book.id);
  } catch (e) {
    toast("上传失败：" + e.message, 4000);
  }
}

/* ---------- 阅读器 ---------- */
async function openBook(id) {
  state.book = await api(`/api/books/${id}`);
  state.page = 1;
  $("#libraryView").classList.add("hidden");
  $("#readerView").classList.remove("hidden");
  $("#backBtn").classList.remove("hidden");
  $("#bookTitle").textContent = state.book.title;
  $("#totalPages").textContent = state.book.total_pages;
  $("#pageInput").max = state.book.total_pages;
  await loadPage(1);
}

function backToLibrary() {
  stopJobPolling();
  state.book = null;
  $("#readerView").classList.add("hidden");
  $("#libraryView").classList.remove("hidden");
  $("#backBtn").classList.add("hidden");
  $("#bookTitle").textContent = "";
  loadLibrary();
}

async function loadPage(n) {
  if (!state.book) return;
  n = Math.max(1, Math.min(state.book.total_pages, n));
  state.page = n;
  $("#pageInput").value = n;
  const { blocks, meta } = await api(`/api/books/${state.book.id}/page/${n}`);
  const rows = $("#rows");
  rows.innerHTML = "";
  for (const b of blocks) {
    const row = document.createElement("div");
    row.className = "row" + (b.type === "h" ? " h" : "");
    const en = document.createElement("div");
    en.className = "cell en";
    en.textContent = b.original;
    const zh = document.createElement("div");
    zh.className = "cell zh" + (b.translation ? "" : " pending");
    zh.textContent = b.translation || (b.original ? "（待翻译）" : "");
    if (b.translation) {
      zh.setAttribute("contenteditable", "true");
      zh.dataset.id = b.id;
      zh.dataset.orig = b.translation;
      zh.addEventListener("blur", () => saveBlockEdit(zh));
    }
    row.appendChild(en);
    row.appendChild(zh);
    rows.appendChild(row);
  }
  const note = (meta && meta.ai_note) || "";
  $("#aiNote").innerHTML = note ? md(note) : "尚未生成，翻译本页后自动产生。";
  $("#userNote").value = (meta && meta.user_note) || "";
}

async function saveBlockEdit(el) {
  const t = el.textContent.trim();
  if (t === el.dataset.orig) return;
  el.dataset.orig = t;
  try {
    await api(`/api/blocks/${el.dataset.id}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ translation: t }),
    });
    toast("译文已保存");
  } catch (e) { toast("保存失败：" + e.message); }
}

function saveUserNoteDebounced() {
  clearTimeout(state.noteTimer);
  state.noteTimer = setTimeout(async () => {
    if (!state.book) return;
    await api(`/api/books/${state.book.id}/page/${state.page}/usernote`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_note: $("#userNote").value }),
    }).catch(() => {});
  }, 800);
}

async function regenerateNote() {
  if (!state.book) return;
  const btn = $("#regenNoteBtn");
  btn.disabled = true;
  $("#aiNote").innerHTML = "重新生成中…";
  try {
    const r = await api(`/api/books/${state.book.id}/page/${state.page}/regenerate-note`, { method: "POST" });
    $("#aiNote").innerHTML = r.ai_note ? md(r.ai_note) : "（本页无需延伸笔记）";
    toast("笔记已重新生成");
  } catch (e) {
    $("#aiNote").innerHTML = "生成失败：" + e.message;
    toast(e.message, 4000);
  } finally {
    btn.disabled = false;
  }
}

/* ---------- 翻译任务 ---------- */
async function translate(scope) {
  if (!state.book) return;
  let body = {};
  if (scope === "page") body = { start: state.page, end: state.page };
  try {
    const res = await api(`/api/books/${state.book.id}/translate`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    toast(`开始翻译 ${res.pages} 页…`);
    pollJob(res.job_id);
  } catch (e) { toast(e.message, 4000); }
}

function pollJob(jobId) {
  stopJobPolling();
  const prog = $("#transProgress");
  state.jobTimer = setInterval(async () => {
    let j;
    try { j = await api(`/api/jobs/${jobId}`); } catch { return; }
    if (j.status === "running" || j.status === "pending") {
      prog.textContent = `翻译中 ${j.done}/${j.total}`;
    } else if (j.status === "done") {
      stopJobPolling();
      prog.textContent = "✓ 完成";
      setTimeout(() => (prog.textContent = ""), 3000);
      state.book = await api(`/api/books/${state.book.id}`);
      loadPage(state.page);
      toast("翻译完成");
    } else if (j.status === "error") {
      stopJobPolling();
      prog.textContent = "";
      toast("翻译出错：" + j.error, 6000);
      loadPage(state.page);
    }
  }, 1200);
}

function stopJobPolling() {
  if (state.jobTimer) { clearInterval(state.jobTimer); state.jobTimer = null; }
}

/* ---------- 导出 ---------- */
function exportBook(fmt) {
  if (!state.book) return;
  window.open(`/api/books/${state.book.id}/export?format=${fmt}`, "_blank");
}

/* ---------- 设置 ---------- */
async function openSettings() {
  const c = await api("/api/config");
  $("#cfgProvider").value = c.provider || "deepseek";
  $("#cfgApiKey").value = "";
  $("#keyHint").textContent = c.api_key_set ? `已设置（${c.api_key_hint}），留空不修改` : "尚未设置";
  $("#cfgBaseUrl").value = c.base_url || "";
  $("#cfgProxy").value = c.proxy || "";
  $("#cfgModel").value = c.model || "";
  $("#cfgTarget").value = c.target_lang || "中文";
  $("#cfgConcurrency").value = c.concurrency || 4;
  $("#cfgMakeNotes").checked = c.make_notes !== false;
  $("#cfgNoteStyle").value = c.note_style || "讲解版";
  $("#cfgOcrMode").value = c.ocr_mode || "auto";
  $("#testResult").textContent = "";
  $("#settingsModal").classList.remove("hidden");
  api("/api/ocr-status").then((s) => {
    $("#ocrHint").textContent = s.available
      ? "✓ 已检测到 OCR 引擎，可识别扫描版 PDF"
      : "未检测到 OCR 引擎：" + (s.detail || "请安装 tesseract-ocr 后重启");
  }).catch(() => {});
}

function collectConfig() {
  return {
    provider: $("#cfgProvider").value,
    api_key: $("#cfgApiKey").value,
    base_url: $("#cfgBaseUrl").value.trim(),
    proxy: $("#cfgProxy").value.trim(),
    model: $("#cfgModel").value.trim(),
    target_lang: $("#cfgTarget").value.trim() || "中文",
    concurrency: parseInt($("#cfgConcurrency").value) || 4,
    make_notes: $("#cfgMakeNotes").checked,
    note_style: $("#cfgNoteStyle").value,
    ocr_mode: $("#cfgOcrMode").value,
  };
}

async function saveSettings() {
  await api("/api/config", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectConfig()),
  });
  $("#settingsModal").classList.add("hidden");
  toast("设置已保存");
}

async function testConnection() {
  const el = $("#testResult");
  el.className = "test-result";
  el.textContent = "测试中…";
  // 先保存当前填写的配置再测试
  await api("/api/config", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(collectConfig()),
  });
  try {
    const r = await api("/api/test-connection", { method: "POST" });
    el.className = "test-result ok";
    el.textContent = "✓ 连接正常，模型回复：" + r.reply;
  } catch (e) {
    el.className = "test-result err";
    el.textContent = "✗ " + e.message;
  }
}

/* 服务商切换时填默认 base_url / model */
function onProviderChange() {
  const p = $("#cfgProvider").value;
  if (p === "deepseek") {
    $("#cfgBaseUrl").value = "https://api.deepseek.com";
    $("#cfgModel").value = "deepseek-chat";
  }
}

/* ---------- 事件绑定 ---------- */
function bind() {
  // 上传
  const dz = $("#dropzone"), fi = $("#fileInput");
  dz.onclick = () => fi.click();
  fi.onchange = (e) => uploadFile(e.target.files[0]);
  ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => {
    e.preventDefault(); dz.classList.add("drag");
  }));
  ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => {
    e.preventDefault(); dz.classList.remove("drag");
  }));
  dz.addEventListener("drop", (e) => uploadFile(e.dataTransfer.files[0]));

  // 导航
  $("#backBtn").onclick = backToLibrary;
  $("#prevPage").onclick = () => loadPage(state.page - 1);
  $("#nextPage").onclick = () => loadPage(state.page + 1);
  $("#pageInput").onchange = (e) => loadPage(parseInt(e.target.value) || 1);
  document.addEventListener("keydown", (e) => {
    if ($("#readerView").classList.contains("hidden")) return;
    if (e.target.tagName === "TEXTAREA" || e.target.isContentEditable) return;
    if (e.key === "ArrowLeft") loadPage(state.page - 1);
    if (e.key === "ArrowRight") loadPage(state.page + 1);
  });

  // 翻译 / 导出
  $("#translateAllBtn").onclick = () => translate("all");
  $("#translatePageBtn").onclick = () => translate("page");
  $("#exportBtn").onclick = (e) => {
    e.stopPropagation();
    const m = $("#exportMenu");
    m.style.display = m.style.display === "block" ? "none" : "block";
  };
  $("#exportMenu").querySelectorAll("a").forEach((a) => a.onclick = () => {
    exportBook(a.dataset.fmt); $("#exportMenu").style.display = "none";
  });
  document.addEventListener("click", () => { $("#exportMenu").style.display = "none"; });

  // 笔记
  $("#userNote").oninput = saveUserNoteDebounced;
  $("#regenNoteBtn").onclick = regenerateNote;

  // 设置
  $("#settingsBtn").onclick = openSettings;
  $("#cancelSettings").onclick = () => $("#settingsModal").classList.add("hidden");
  $("#saveSettings").onclick = saveSettings;
  $("#testBtn").onclick = testConnection;
  $("#cfgProvider").onchange = onProviderChange;
}

(async function init() {
  bind();
  await loadLibrary();
  // 首次无 Key 时提示
  const c = await api("/api/config");
  if (!c.api_key_set) {
    toast("提示：请先在「设置」中填写 DeepSeek API Key", 4000);
  }
})();

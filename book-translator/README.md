# 📖 Book Translator · 英文书双语阅读器

把整本英文 PDF 自动翻译成准确中文，**左右对照阅读**，并在旁边**生成 AI 笔记备注**。
底层默认使用 **DeepSeek**（兼容 OpenAI 接口，国内访问稳定、便宜），也可切换到任意 OpenAI 兼容服务（含 Claude 兼容网关）。

可以作为本地网页阅读器运行，也可以打包成 **Windows .exe / macOS .app 桌面程序**。

---

## 功能

- 📥 上传整本英文 PDF，自动抽取文本（按段落、自动识别标题、合并断行）
- 🔍 **扫描版 PDF 支持**：无文字层的扫描页自动 OCR 识别（基于 Tesseract）
- 🔁 逐段翻译，**英文 / 中文左右对照**，对齐到段落
- 📝 每页自动生成 **AI 笔记**（要点概括 + 难点讲解 + 重点词汇释义，三种风格可选）
- ✍️ 中文译文可**点击直接修改**，并可在每页写**自己的笔记**（自动保存）
- ⚡ 多页并发翻译，带进度显示；翻译结果**本地缓存**，重开不用重译
- 💾 一键导出**带目录(可点击书签)的双语 PDF / HTML / Word(docx) / Markdown**
- 🔒 API Key 只存在本机（`~/.book-translator/config.json`），不上传任何服务器

---

## 快速开始（本地运行）

需要 Python 3.9+。

```bash
cd book-translator
pip install -r requirements.txt

# 桌面窗口模式（需要 pywebview）
python app.py

# 或浏览器模式（不依赖 pywebview，自动打开默认浏览器）
BT_BROWSER=1 python app.py      # Windows: set BT_BROWSER=1 && python app.py
```

首次启动后点右上角 **⚙ 设置**，填入 **DeepSeek API Key**
（在 https://platform.deepseek.com 申请），点「测试连接」确认可用，保存即可。

然后：把 PDF 拖进首页 → 打开 → 点「翻译全书」或「译本页」→ 左右对照阅读。

---

## 打包成桌面程序

先安装依赖和打包工具：`pip install -r requirements.txt pyinstaller`

- **Windows**：双击运行 `build\build_windows.bat`，产物在 `dist\BookTranslator\`
- **macOS**：`bash build/build_macos.sh`，产物为 `dist/BookTranslator.app`

> 打包需在对应系统上进行（Windows 上打 exe，Mac 上打 app）。

---

## 扫描版 PDF（OCR）

如果你的书是**扫描件（纯图片、没有文字层）**，需要额外安装 OCR 引擎 Tesseract：

- **Windows**：到 https://github.com/UB-Mannheim/tesseract/wiki 下载安装包安装即可
- **macOS**：`brew install tesseract`
- **Ubuntu/Debian**：`sudo apt-get install tesseract-ocr`

然后 `pip install pytesseract pillow`（已含在 requirements.txt 中）。

在「设置 → 扫描版 OCR」里可选：
- **自动**（默认）：只对没有文字层的扫描页做 OCR，正常电子书不受影响
- **关闭**：从不 OCR
- **强制**：每页都 OCR（适合排版复杂、文字层混乱的 PDF，速度较慢）

> OCR 会在上传解析阶段进行，扫描版大书解析时间较长，请耐心等待。
> 设置里会显示是否已检测到 OCR 引擎。

---

## 导出带目录的 PDF

导出菜单里选「**PDF（带目录）**」会生成一份双语对照 PDF：
封面 + **可点击目录** + 正文（英中左右对照）+ AI/个人笔记，
并带 **PDF 书签（大纲）**，按章节标题跳转。中文使用内置字体，无需另装字体。

---

## 切换大模型

在「设置」里：

| 服务商 | Base URL | 模型示例 |
|--------|----------|----------|
| DeepSeek（默认） | `https://api.deepseek.com` | `deepseek-chat` |
| 自定义（OpenAI 兼容/Claude 网关） | 你的接口地址 | 对应模型名 |

只要接口兼容 OpenAI 的 `/v1/chat/completions` 格式即可直接接入。

---

## 目录结构

```
book-translator/
├── app.py                 # 入口：启动本地服务 + 桌面窗口
├── requirements.txt
├── backend/
│   ├── config.py          # 配置与 API Key 存储（本机）
│   ├── storage.py         # SQLite：书籍/文本块/译文/笔记/缓存
│   ├── pdf_extract.py     # PDF → 段落文本块（含扫描页 OCR 兜底）
│   ├── ocr.py            # 扫描版 PDF 的 Tesseract OCR
│   ├── translator.py      # DeepSeek 翻译 + AI 笔记
│   ├── jobs.py            # 后台并发翻译任务与进度
│   ├── export.py          # 导出 HTML / docx / Markdown
│   └── server.py          # Flask REST 接口
├── frontend/              # 阅读器界面（原生 HTML/CSS/JS）
│   ├── index.html
│   ├── style.css
│   └── app.js
└── build/                 # 打包脚本
```

数据保存在用户目录 `~/.book-translator/`（书库数据库 `library.db` + 配置 `config.json`）。

---

## 常见问题

- **翻译报错 "尚未设置 API Key"**：到设置里填 Key 并保存。
- **扫描版 PDF 没文字**：本工具读取的是 PDF 内嵌文本，纯图片扫描版需要先做 OCR。
- **费用**：DeepSeek 价格很低，整本书通常只需很少的费用；已翻译的页会缓存，不重复计费。
- **翻译慢**：调高「设置 → 并发页数」（最大 8）。

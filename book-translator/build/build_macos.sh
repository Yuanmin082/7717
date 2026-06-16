#!/usr/bin/env bash
# 打包成 macOS .app（在 macOS 上运行此脚本）
# 需先：pip install -r requirements.txt pyinstaller
set -e
cd "$(dirname "$0")/.."
pyinstaller --noconfirm --clean \
  --name "BookTranslator" \
  --windowed \
  --add-data "frontend:frontend" \
  --hidden-import fitz \
  app.py
echo "完成，产物在 dist/BookTranslator.app"

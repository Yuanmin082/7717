@echo off
chcp 65001 >nul
title Book Translator - 英文书双语阅读器
cd /d "%~dp0"

REM 关闭系统代理，避免 Clash 等代理导致无法直连 DeepSeek
set HTTP_PROXY=
set HTTPS_PROXY=
set ALL_PROXY=

REM 检查依赖；首次运行若缺失，自动用国内镜像安装
python -c "import flask, fitz, requests, docx, reportlab" 2>nul
if errorlevel 1 (
  echo ============================================================
  echo  首次运行，正在安装所需组件（使用清华镜像，约 1-2 分钟）...
  echo ============================================================
  python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  if errorlevel 1 (
    echo.
    echo [安装失败] 请把上面的红色信息截图反馈。
    pause
    exit /b 1
  )
)

echo.
echo 正在启动 Book Translator，程序窗口稍后会自动弹出...
echo （此黑色窗口请勿关闭，关闭它程序也会退出）
echo.
python app.py

if errorlevel 1 (
  echo.
  echo [启动出错] 请把上面的红色信息截图反馈。
  pause
)

@echo off
REM 打包成 Windows 单文件 exe（在 Windows 上运行此脚本）
REM 需先：pip install -r requirements.txt pyinstaller
cd /d "%~dp0\.."
pyinstaller --noconfirm --clean ^
  --name "BookTranslator" ^
  --windowed ^
  --add-data "frontend;frontend" ^
  --hidden-import fitz ^
  app.py
echo.
echo 完成，产物在 dist\BookTranslator\
pause

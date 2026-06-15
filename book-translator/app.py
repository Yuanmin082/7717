"""Book Translator 入口。

- 桌面模式（默认）：用 pywebview 打开原生窗口，内嵌本地阅读器界面。
- 浏览器模式：设置环境变量 BT_BROWSER=1 时，仅启动本地服务并自动打开浏览器。

打包成 .exe / .app 见 build/ 目录。
"""
import os
import socket
import threading
import time
import webbrowser

from backend.server import create_app


def _free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _run_server(app, port: int):
    app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False)


def main():
    app = create_app()
    port = int(os.environ.get("BT_PORT", _free_port()))
    url = f"http://127.0.0.1:{port}"

    server_thread = threading.Thread(target=_run_server, args=(app, port), daemon=True)
    server_thread.start()
    time.sleep(0.8)

    if os.environ.get("BT_BROWSER") == "1":
        print(f"Book Translator 已启动：{url}")
        webbrowser.open(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass
        return

    try:
        import webview  # pywebview
    except ImportError:
        print("未安装 pywebview，改用浏览器模式打开：", url)
        webbrowser.open(url)
        while True:
            time.sleep(3600)
        return

    webview.create_window("Book Translator · 英中双语阅读器", url, width=1280, height=860,
                          min_size=(900, 600))
    webview.start()


if __name__ == "__main__":
    main()

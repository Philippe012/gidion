import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

import webview

from app.ui.server import run as run_flask
from app import config

import os
import logging

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
os.chdir(BASE_DIR)

LOG_FILE = BASE_DIR / "gidion.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

logging.info("Gidion desktop starting; CWD=%s", BASE_DIR)


def _resource_path(relative_path: str) -> str:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base_path / relative_path)


ICON_PATH = _resource_path("assets/gidion-logo.ico")


def _wait_for_server(host: str, port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _open_browser(url: str) -> bool:
    try:
        webbrowser.open(url, new=0)
        return True
    except Exception:
        logging.exception("Failed to open browser")
        return False


def main():
    server_thread = threading.Thread(target=run_flask, daemon=True)
    server_thread.start()

    if not _wait_for_server(config.UI_HOST, config.UI_PORT):
        print("Gidion server did not start in time.", file=sys.stderr)
        sys.exit(1)

    url = f"http://{config.UI_HOST}:{config.UI_PORT}/"
    logging.info("Opening UI at %s", url)

    try:
        webview.create_window(
            "Gidion",
            url,
            width=960,
            height=820,
            min_size=(720, 600),
            resizable=True,
        )

        icon = ICON_PATH if Path(ICON_PATH).exists() else None
        webview.start(
            gui="edgechromium" if sys.platform == "win32" else None,
            icon=icon,
        )
    except Exception:
        logging.exception("pywebview startup failed; falling back to browser")
        print("[desktop] pywebview failed; opening browser instead.", file=sys.stderr)

        if _open_browser(url):
            print("[desktop] Opened browser. The app will stay running in the background.", file=sys.stderr)
            while True:
                time.sleep(60)
        else:
            print("[desktop] Browser fallback also failed.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Unhandled error in desktop")
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                None,
                f"Error starting Gidion. See {LOG_FILE}",
                "Gidion Error",
                0,
            )
        except Exception:
            pass
        raise
import socket
import sys
import threading
import time
import webbrowser
import os
import logging
from pathlib import Path

from app import config

BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
os.chdir(BASE_DIR)

LOG_FILE = BASE_DIR / "gidion.log"
logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    force=True,
)

logging.info("Gidion desktop starting; CWD=%s", BASE_DIR)


def _resource_path(relative_path: str) -> str:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base_path / relative_path)


def _wait_for_server(host: str, port: int, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _server_thread():
    try:
        from app.ui.server import run as run_flask
        run_flask()
    except Exception:
        logging.exception("Server thread crashed")
        raise


def main():
    server_thread = threading.Thread(target=_server_thread, daemon=False)
    server_thread.start()

    if not _wait_for_server(config.UI_HOST, config.UI_PORT):
        logging.error("Gidion server did not start in time.")
        sys.exit(1)

    url = f"http://{config.UI_HOST}:{config.UI_PORT}/"
    logging.info("Opening UI at %s", url)

    try:
        import webview

        webview.create_window(
            "Gidion",
            url,
            width=960,
            height=820,
            min_size=(720, 600),
            resizable=True,
        )

        icon = _resource_path("assets/gidion-logo.ico")
        if not Path(icon).exists():
            icon = None

        webview.start(
            gui="edgechromium" if sys.platform == "win32" else None,
            icon=icon,
        )
    except Exception:
        logging.exception("pywebview failed; falling back to browser")
        try:
            webbrowser.open(url)
        except Exception:
            logging.exception("Browser fallback also failed")

        print(f"[desktop] Gidion is running. Open this URL in your browser: {url}", file=sys.stderr)
        while True:
            time.sleep(60)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logging.exception("Unhandled error in desktop")
        raise
"""
Desktop wrapper for Gidion.

Wraps the existing Flask UI (app/ui/server.py) in a native window using
pywebview, so the user sees a window titled "Gidion" instead of a browser
tab pointed at http://127.0.0.1:5000.

This file is a launcher only. It imports app and run from server.py
unchanged and does not modify any existing Flask code. Since it's a
local-only app served on 127.0.0.1, using pywebview's own window instead
of a system browser also avoids ever showing an address bar.
"""
import socket
import sys
import threading
import time

import webview

# Adjust this import if server.py lives somewhere other than app/ui/server.py
from app.ui.server import app as flask_app, run as run_flask
from app import config


def _wait_for_server(host: str, port: int, timeout: float = 15.0) -> bool:
    """Poll the port until Flask is actually accepting connections."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def main():
    # run() calls app.run(host=..., port=..., debug=False) — debug=False
    # means Flask's reloader is already disabled, so this is safe to run
    # in a background thread of a frozen PyInstaller exe.
    server_thread = threading.Thread(target=run_flask, daemon=True)
    server_thread.start()

    if not _wait_for_server(config.UI_HOST, config.UI_PORT):
        print("Gidion server did not start in time.", file=sys.stderr)
        sys.exit(1)

    webview.create_window(
        "Gidion",
        f"http://{config.UI_HOST}:{config.UI_PORT}/",
        width=960,
        height=820,
        min_size=(720, 600),
        resizable=True,
    )
    # gui="edgechromium" is the Windows default when pywebview detects
    # WebView2; being explicit avoids it silently falling back to a
    # different renderer during a frozen build.
    webview.start(gui="edgechromium" if sys.platform == "win32" else None)


if __name__ == "__main__":
    main()
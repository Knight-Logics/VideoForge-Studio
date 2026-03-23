from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

from waitress import serve


def _open_browser(url: str) -> None:
    time.sleep(1.5)
    webbrowser.open(url)


def main() -> None:
    runtime_root = Path(__file__).resolve().parent
    if getattr(sys, 'frozen', False):
        runtime_root = Path(sys.executable).resolve().parent

    os.environ.setdefault('VIDEOFORGE_RUNTIME_ROOT', str(runtime_root))
    from app import app

    url = 'http://127.0.0.1:5050'
    threading.Thread(target=_open_browser, args=(url,), daemon=True).start()
    serve(app, listen='127.0.0.1:5050', max_request_body_size=4294967296)


if __name__ == '__main__':
    main()

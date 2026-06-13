from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from waitress import serve

HOST = '127.0.0.1'
DEFAULT_PORT = 5055
PORT_SCAN_START = 5055
PORT_SCAN_END = 5064
HEALTH_PATH = '/health'
SERVICE_ID = 'videoforge-studio'
MAX_REQUEST_BODY_SIZE = 4294967296


def _get_runtime_root() -> Path:
    runtime_root = Path(__file__).resolve().parent
    if getattr(sys, 'frozen', False):
        runtime_root = Path(sys.executable).resolve().parent
    return runtime_root


def _get_resource_root() -> Path:
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        return Path(getattr(sys, '_MEIPASS'))
    return Path(__file__).resolve().parent


def _port_in_use(port: int) -> bool:
    try:
        with socket.create_connection((HOST, port), timeout=0.35):
            return True
    except OSError:
        return False


def _is_videoforge_health(port: int) -> bool:
    url = f'http://{HOST}:{port}{HEALTH_PATH}'
    try:
        with urllib.request.urlopen(url, timeout=1.0) as response:
            payload = json.loads(response.read().decode('utf-8'))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, OSError):
        return False

    if payload.get('service') == SERVICE_ID:
        return True

    app_name = str(payload.get('app', '')).lower()
    return 'videoforge' in app_name or 'autotop5' in app_name


def _resolve_port() -> int:
    for env_key in ('VIDEOFORGE_PORT', 'APP_PORT', 'PORT'):
        raw = os.environ.get(env_key, '').strip()
        if raw.isdigit():
            return int(raw)

    for port in range(PORT_SCAN_START, PORT_SCAN_END + 1):
        if not _port_in_use(port):
            return port

    raise RuntimeError(
        f'VideoForge Studio could not find a free local port between {PORT_SCAN_START} and {PORT_SCAN_END}. '
        'Close other local apps or set VIDEOFORGE_PORT.'
    )


def _configure_runtime_port(port: int) -> str:
    os.environ['VIDEOFORGE_PORT'] = str(port)
    os.environ['APP_PORT'] = str(port)
    os.environ['PORT'] = str(port)
    os.environ.setdefault('APP_HOST', HOST)
    os.environ.setdefault('APP_BASE_URL', f'http://{HOST}:{port}')
    return f'http://{HOST}:{port}'


def _open_browser(url: str) -> None:
    time.sleep(1.5)
    webbrowser.open(url)


def _run_server() -> None:
    os.environ.setdefault('VIDEOFORGE_RUNTIME_ROOT', str(_get_runtime_root()))
    from app import app

    port = int(os.environ.get('APP_PORT', str(DEFAULT_PORT)))
    serve(app, host=HOST, port=port, max_request_body_size=MAX_REQUEST_BODY_SIZE)


def _wait_for_videoforge_server(port: int, timeout_seconds: float = 25.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _is_videoforge_health(port):
            return True
        time.sleep(0.15)
    return False


def _should_use_desktop_ui() -> bool:
    mode = os.environ.get('VIDEOFORGE_UI_MODE', 'desktop').strip().lower()
    if mode == 'browser':
        return False

    preferred_engine = os.environ.get('VIDEOFORGE_UI_ENGINE', 'webview').strip().lower()

    if preferred_engine == 'webview':
        try:
            import webview  # noqa: F401
            return True
        except ImportError:
            pass

    try:
        import PySide6  # noqa: F401
        return True
    except ImportError:
        pass

    try:
        import webview  # noqa: F401
        return True
    except ImportError:
        return False


def _run_browser_mode(local_url: str, port: int) -> None:
    if _port_in_use(port) and not _is_videoforge_health(port):
        raise RuntimeError(
            f'Port {port} is already used by another app (likely Knight Command on 5050). '
            'Close that app or set VIDEOFORGE_PORT to a free port.'
        )

    threading.Thread(target=_open_browser, args=(local_url,), daemon=True).start()
    _run_server()


def _run_webview_mode(local_url: str, port: int) -> int:
    import webview

    os.environ['VIDEOFORGE_DESKTOP_SHELL'] = 'pywebview'
    if isinstance(getattr(webview, 'settings', None), dict):
        webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True

    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()

    if not _wait_for_videoforge_server(port):
        raise RuntimeError(
            f'VideoForge Studio could not start its local server on {local_url}. '
            'Another app may already be using that port.'
        )

    webview.create_window(
        'VideoForge Studio',
        local_url,
        width=1440,
        height=960,
        min_size=(1180, 760),
        confirm_close=True,
    )
    webview.start(gui='edgechromium', debug=False, private_mode=False)
    return 0


def _run_desktop_mode(local_url: str, port: int) -> int:
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QAction, QDesktopServices, QIcon
    from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
    from PySide6.QtWebEngineCore import QWebEnginePage
    from PySide6.QtWebEngineWidgets import QWebEngineView

    internal_hosts = {HOST, 'localhost'}

    def is_internal_url(url: QUrl) -> bool:
        if not url.isValid():
            return False
        scheme = url.scheme().lower()
        host = url.host().lower()
        return scheme in {'http', 'https'} and host in internal_hosts

    class VideoForgePage(QWebEnginePage):
        def acceptNavigationRequest(self, url, nav_type, is_main_frame):
            if nav_type == QWebEnginePage.NavigationTypeLinkClicked and not is_internal_url(url):
                QDesktopServices.openUrl(url)
                return False
            return super().acceptNavigationRequest(url, nav_type, is_main_frame)

        def createWindow(self, _window_type):
            popup_page = QWebEnginePage(self.profile(), self)
            popup_page.urlChanged.connect(QDesktopServices.openUrl)
            return popup_page

    class VideoForgeWindow(QMainWindow):
        def __init__(self) -> None:
            super().__init__()
            self.setWindowTitle('VideoForge Studio')
            self.resize(1440, 960)
            self.setMinimumSize(1180, 760)

            icon_path = _get_resource_root() / 'static' / 'app-icon.png'
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))

            self.view = QWebEngineView(self)
            self.page = VideoForgePage(self.view)
            self.view.setPage(self.page)
            self.setCentralWidget(self.view)

            toolbar = self.addToolBar('Navigation')
            toolbar.setMovable(False)

            refresh_action = QAction('Refresh', self)
            refresh_action.triggered.connect(self.view.reload)
            toolbar.addAction(refresh_action)

            open_browser_action = QAction('Open In Browser', self)
            open_browser_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(local_url)))
            toolbar.addAction(open_browser_action)

            diagnostics_action = QAction('Diagnostics', self)
            diagnostics_action.triggered.connect(
                lambda: QDesktopServices.openUrl(QUrl(f'{local_url}/diagnostics'))
            )
            toolbar.addAction(diagnostics_action)

            self.view.load(QUrl(local_url))

    os.environ['VIDEOFORGE_DESKTOP_SHELL'] = 'pyside6'
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()

    if not _wait_for_videoforge_server(port):
        raise RuntimeError(
            f'VideoForge Studio could not start its local server on {local_url}. '
            'Another app may already be using that port.'
        )

    app = QApplication(sys.argv)
    app.setApplicationName('VideoForge Studio')

    icon_path = _get_resource_root() / 'static' / 'app-icon.png'
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = VideoForgeWindow()
    window.show()
    return app.exec()


def main() -> None:
    port = _resolve_port()
    local_url = _configure_runtime_port(port)

    if _port_in_use(port) and not _is_videoforge_health(port):
        raise RuntimeError(
            f'Port {port} is already used by another app. Knight Command uses 5050; '
            'VideoForge now defaults to 5055+. Close the conflicting app or set VIDEOFORGE_PORT.'
        )

    if not _should_use_desktop_ui():
        _run_browser_mode(local_url, port)
        return

    preferred_engine = os.environ.get('VIDEOFORGE_UI_ENGINE', 'webview').strip().lower()

    try:
        if preferred_engine == 'webview':
            try:
                raise SystemExit(_run_webview_mode(local_url, port))
            except ImportError:
                pass
            raise SystemExit(_run_desktop_mode(local_url, port))

        try:
            raise SystemExit(_run_desktop_mode(local_url, port))
        except ImportError:
            pass
        raise SystemExit(_run_webview_mode(local_url, port))
    except RuntimeError as error:
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox

            qt_app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, 'VideoForge Studio', str(error))
            raise SystemExit(1)
        except ImportError:
            raise SystemExit(str(error))


if __name__ == '__main__':
    main()

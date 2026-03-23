from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

from waitress import serve

HOST = '127.0.0.1'
PORT = 5050
LOCAL_URL = f'http://{HOST}:{PORT}'
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


def _open_browser(url: str) -> None:
    time.sleep(1.5)
    webbrowser.open(url)


def _run_server() -> None:
    os.environ.setdefault('VIDEOFORGE_RUNTIME_ROOT', str(_get_runtime_root()))
    from app import app

    serve(app, listen=f'{HOST}:{PORT}', max_request_body_size=MAX_REQUEST_BODY_SIZE)


def _wait_for_server(timeout_seconds: float = 20.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection((HOST, PORT), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.15)
    return False


def _should_use_desktop_ui() -> bool:
    mode = os.environ.get('VIDEOFORGE_UI_MODE', 'desktop').strip().lower()
    if mode == 'browser':
        return False

    try:
        import webview  # noqa: F401
        return True
    except ImportError:
        pass

    try:
        import PySide6  # noqa: F401
    except ImportError:
        return False
    return True


def _run_browser_mode() -> None:
    threading.Thread(target=_open_browser, args=(LOCAL_URL,), daemon=True).start()
    _run_server()


def _run_webview_mode() -> int:
    import webview

    os.environ['VIDEOFORGE_DESKTOP_SHELL'] = 'pywebview'
    if isinstance(getattr(webview, 'settings', None), dict):
        webview.settings['OPEN_EXTERNAL_LINKS_IN_BROWSER'] = True

    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()

    if not _wait_for_server():
        raise RuntimeError('VideoForge Studio could not start the local server on 127.0.0.1:5050.')

    icon_path = _get_resource_root() / 'static' / 'app-icon.png'
    webview.create_window(
        'VideoForge Studio',
        LOCAL_URL,
        width=1440,
        height=960,
        min_size=(1180, 760),
        confirm_close=True,
        icon=str(icon_path) if icon_path.exists() else None,
    )
    webview.start(gui='edgechromium', debug=False, private_mode=False)
    return 0


def _run_desktop_mode() -> int:
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
            open_browser_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl(LOCAL_URL)))
            toolbar.addAction(open_browser_action)

            self.view.load(QUrl(LOCAL_URL))

    os.environ['VIDEOFORGE_DESKTOP_SHELL'] = 'pyside6'
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()

    if not _wait_for_server():
        raise RuntimeError('VideoForge Studio could not start the local server on 127.0.0.1:5050.')

    app = QApplication(sys.argv)
    app.setApplicationName('VideoForge Studio')

    icon_path = _get_resource_root() / 'static' / 'app-icon.png'
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = VideoForgeWindow()
    window.show()
    return app.exec()


def main() -> None:
    if not _should_use_desktop_ui():
        _run_browser_mode()
        return

    try:
        try:
            raise SystemExit(_run_webview_mode())
        except ImportError:
            pass
        raise SystemExit(_run_desktop_mode())
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

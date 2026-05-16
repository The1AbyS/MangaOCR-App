import sys
from pathlib import Path

from PySide6.QtGui import QIcon


APP_USER_MODEL_ID = "The1AbyS.MangaOCRApp.App"


def set_windows_app_id():
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception:
        pass


def icon_path(app_dir):
    app_dir = Path(app_dir)
    for name in ("Mocr.ico", "Mocr.png"):
        path = app_dir / "app" / "ui" / "icons" / name
        if path.exists():
            return path
    return None


def load_app_icon(app_dir):
    path = icon_path(app_dir)
    return QIcon(str(path)) if path else QIcon()


def apply_windows_window_icon(window, app_dir):
    if sys.platform != "win32":
        return
    path = icon_path(app_dir)
    if not path:
        return
    try:
        import ctypes

        hwnd = int(window.winId())
        hicon_big = ctypes.windll.user32.LoadImageW(None, str(path), 1, 32, 32, 0x0010)
        hicon_small = ctypes.windll.user32.LoadImageW(None, str(path), 1, 16, 16, 0x0010)
        if hicon_big:
            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon_big)
        if hicon_small:
            ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon_small)
        window._native_icon_handles = (hicon_big, hicon_small)
    except Exception:
        pass

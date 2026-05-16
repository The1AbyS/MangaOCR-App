import sys
from pathlib import Path

from PySide6.QtGui import QFont
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.core.app_bootstrap import apply_windows_window_icon, load_app_icon, set_windows_app_id
from app.ui.main_window.window import MainWindow


if __name__ == "__main__":
    app_dir = Path(__file__).resolve().parent
    set_windows_app_id()

    app = QApplication(sys.argv)
    icon = load_app_icon(app_dir)
    app.setWindowIcon(icon)

    font = QFont()
    font.setFamilies(["Segoe UI", "BIZ UDGothic"])
    app.setFont(font)

    window = MainWindow()
    window.setWindowIcon(icon)
    window.show()
    QTimer.singleShot(0, lambda: apply_windows_window_icon(window, app_dir))
    sys.exit(app.exec())

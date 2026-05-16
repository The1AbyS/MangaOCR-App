from PySide6.QtCore import QPoint, QSettings, QSize, Qt


def restore_window_state(window):
    size = window.settings.value("window_size", QSize(1000, 700), type=QSize)
    pos = window.settings.value("window_pos", QPoint(100, 100), type=QPoint)

    window.resize(size)
    window.move(pos)

    was_maximized = window.settings.value("window_maximized", False, type=bool)
    if was_maximized:
        window.setWindowState(window.windowState() | Qt.WindowMaximized)

    layout_settings = QSettings("MangaOCR", "Layout")
    state = layout_settings.value("state")
    if state:
        window.restoreState(state)


def save_window_state(window):
    window.settings.setValue("window_maximized", window.isMaximized())

    if not window.isMaximized():
        window.settings.setValue("window_size", window.size())
        window.settings.setValue("window_pos", window.pos())

    layout_settings = QSettings("MangaOCR", "Layout")
    layout_settings.setValue("state", window.saveState())

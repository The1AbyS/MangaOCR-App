from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDockWidget


def create_docks(window):
    window.dock_list = _make_dock(window, "Страницы", window.list_widget, "dock_pages")
    window.addDockWidget(Qt.LeftDockWidgetArea, window.dock_list)

    window.dock_translation_progress = _make_dock(
        window,
        "Прогресс перевода",
        window.translation_progress,
        "dock_translation_progress",
    )
    window.addDockWidget(Qt.LeftDockWidgetArea, window.dock_translation_progress)
    window.splitDockWidget(window.dock_translation_progress, window.dock_list, Qt.Vertical)

    window.dock_text = _make_dock(window, "Текст", window.text_export_panel, "dock_text")
    window.addDockWidget(Qt.RightDockWidgetArea, window.dock_text)

    window.dock_dict = _make_dock(window, "Jardic", window.jardic_widget, "dock_dict")
    window.addDockWidget(Qt.RightDockWidgetArea, window.dock_dict)

    window.dock_rawkuma = _make_dock(window, "Rawkuma", window.rawkuma_widget, "dock_rawkuma")
    window.addDockWidget(Qt.RightDockWidgetArea, window.dock_rawkuma)

def _make_dock(window, title, widget, object_name):
    dock = QDockWidget(title, window)
    dock.setWidget(widget)
    dock.setFeatures(
        QDockWidget.DockWidgetMovable |
        QDockWidget.DockWidgetClosable
    )
    dock.setObjectName(object_name)
    return dock

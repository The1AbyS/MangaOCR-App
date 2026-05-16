from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QFileDialog, QMenu, QToolBar, QToolButton


def create_actions(window):
    window.open_folder_act = QAction("Открыть папку", window)
    window.open_folder_act.setShortcut("Ctrl+O")
    window.open_folder_act.setToolTip("Открыть папку с изображениями")
    window.open_folder_act.triggered.connect(window.action_open_folder)
    window.recent_menu = QMenu(window)
    window.recent_menu.aboutToShow.connect(window.update_recent_menu)
    window.open_folder_act.setMenu(window.recent_menu)

    window.show_frames_act = QAction("Отображение", window)

    window.show_frames_menu = QMenu(window)
    window.show_frames_toggle = QAction("Фреймы", window, checkable=True)
    window.show_frames_toggle.setChecked(False)
    window.show_frames_toggle.triggered.connect(window.toggle_show_frames)

    window.show_numbers_toggle = QAction("Номера боксов", window, checkable=True)
    window.show_numbers_toggle.setChecked(False)
    window.show_numbers_toggle.triggered.connect(window.toggle_show_numbers_boxes)

    window.show_frames_menu.addAction(window.show_frames_toggle)
    window.show_frames_menu.addAction(window.show_numbers_toggle)
    window.show_frames_act.setMenu(window.show_frames_menu)

    window.batch_act = QAction("Обработать всё", window)
    window.batch_act.setToolTip("Обработать все страницы")
    window.batch_act.triggered.connect(window.action_batch_process)

    window.export_act = QAction("Сохранить как...", window)
    window.export_act.setToolTip("Экспортировать текст")
    window.export_act.triggered.connect(window.action_export_text)

    window.switch_central_act = QAction("Показать менеджер проектов", window)
    window.switch_central_act.triggered.connect(window.switch_central)
    window.switch_central_act.setShortcut("Tab")
    window.addAction(window.switch_central_act)

    window.previous_image_act = QAction("Предыдущее изображение", window)
    window.previous_image_act.setShortcut("Up")
    window.previous_image_act.triggered.connect(window.previous_image)
    window.addAction(window.previous_image_act)

    window.next_image_act = QAction("Следующее изображение", window)
    window.next_image_act.setShortcut("Down")
    window.next_image_act.triggered.connect(window.next_image)
    window.addAction(window.next_image_act)

    window.parser_act = QAction("Загрузить изображения из URL", window)
    window.parser_act.triggered.connect(window.action_parser)

    window.clipboard_act = QAction("Буфер обмена", window)
    window.clipboard_act.triggered.connect(window.clipboard_action)
    window.addAction(window.clipboard_act)
    window.clipboard_act.setShortcut("Ctrl+V")

    window.refresh_current_act = QAction("Сбросить кэш", window)
    window.refresh_current_act.triggered.connect(window.refresh_current)
    window.addAction(window.refresh_current_act)
    window.refresh_current_act.setShortcut("Ctrl+R")

    window.delete_current_act = QAction("Удалить текущую страницу из списка", window)
    window.delete_current_act.triggered.connect(window.delete_from_list)
    window.addAction(window.delete_current_act)
    window.delete_current_act.setShortcut("Del")

    window.window_button = QToolButton()
    window.window_button.setText("Окна")
    window.window_button.setPopupMode(QToolButton.MenuButtonPopup)
    window.window_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
    window.view_menu = QMenu(window)
    window.view_menu.addAction(window.dock_list.toggleViewAction())
    window.view_menu.addAction(window.dock_translation_progress.toggleViewAction())
    window.view_menu.addAction(window.dock_text.toggleViewAction())
    window.view_menu.addAction(window.dock_dict.toggleViewAction())
    window.view_menu.addAction(window.dock_rawkuma.toggleViewAction())
    window.window_button.setMenu(window.view_menu)


def create_toolbar(window):
    toolbar = QToolBar("Main")
    toolbar.setObjectName("main_toolbar")
    toolbar.setMovable(False)

    window.addToolBar(toolbar)

    toolbar.addAction(window.open_folder_act)
    toolbar.addAction(window.show_frames_act)
    toolbar.addAction(window.batch_act)
    toolbar.addAction(window.export_act)
    toolbar.addWidget(window.window_button)



def action_open_folder(window):
    folder = QFileDialog.getExistingDirectory(window, "Р’С‹Р±РµСЂРёС‚Рµ РїР°РїРєСѓ СЃ РёР·РѕР±СЂР°Р¶РµРЅРёСЏРјРё")
    if folder:
        window.load_folder(Path(folder))


def switch_central(window):
    window.central_stack.setCurrentIndex(0 if window.central_stack.currentIndex() else 1)


def toggle_show_frames(window, checked):
    window.show_frames = checked
    window.show_frames_and_numbers_boxes()


def toggle_show_numbers_boxes(window, checked):
    window.show_numbers_boxes = checked
    window.show_frames_and_numbers_boxes()


def update_recent_menu(window):
    window.recent_menu.clear()
    folders = window.cache_folder.get_all()
    if not folders:
        window.recent_menu.addAction("(РїСѓСЃС‚Рѕ)").setEnabled(False)
        return

    for path in folders:
        act = window.recent_menu.addAction(str(path))
        act.triggered.connect(lambda checked=False, p=path: window.load_folder(p))
    window.recent_menu.addSeparator()


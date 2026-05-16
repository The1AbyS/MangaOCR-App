from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMainWindow

from . import model_loading
from .actions import (
    action_open_folder,
    create_actions,
    create_toolbar,
    switch_central,
    toggle_show_frames,
    toggle_show_numbers_boxes,
    update_recent_menu,
)
from .layout import create_central, create_statusbar, create_widgets
from .state import restore_window_state as _restore_window_state, save_window_state
from ..workflows import batch_processing
from ..workflows import export_text
from ..workflows import image_import
from ..workflows import ocr_flow
from ..workflows import page_list
from ..workflows import preview_scene
from ...core.cache import OCRCache
from ...core.recent_folders import RecentFolders
from ...ignore import ignore_warnings

ignore_warnings()

class MainWindow(QMainWindow):
    __version__ = "Alpha 0.2.3.0"

    restore_window_state = _restore_window_state
    start_models_load = model_loading.start_models_load
    on_models_loaded = model_loading.on_models_loaded

    _create_actions = create_actions
    _create_toolbar = create_toolbar
    _create_widgets = create_widgets
    _create_central = create_central
    _create_statusbar = create_statusbar

    action_open_folder = action_open_folder
    switch_central = switch_central
    toggle_show_frames = toggle_show_frames
    toggle_show_numbers_boxes = toggle_show_numbers_boxes
    update_recent_menu = update_recent_menu

    action_parser_from_rawkuma = image_import.action_parser_from_rawkuma
    clipboard_action = image_import.clipboard_action
    action_parser = image_import.action_parser
    on_images_downloaded = image_import.on_images_downloaded

    show_frames_and_numbers_boxes = preview_scene.refresh_display_options
    show_preview = preview_scene.show_preview

    load_folder = page_list.load_folder
    update_translation_progress = page_list.update_translation_progress
    on_item_clicked = page_list.on_item_clicked
    on_ocr_progress = page_list.on_ocr_progress
    is_cached = page_list.is_cached
    next_image = page_list.next_image
    previous_image = page_list.previous_image
    show_list_menu = page_list.show_list_menu
    delete_from_list = page_list.delete_from_list
    show_file_info = page_list.show_file_info
    refresh_current = page_list.refresh_current

    action_batch_process = batch_processing.action_batch_process
    _on_batch_item_started = batch_processing.on_batch_item_started
    _on_batch_item_finished = batch_processing.on_batch_item_finished
    _on_batch_stage_changed = batch_processing.on_batch_stage_changed
    _on_batch_stage_progress = batch_processing.on_batch_stage_progress
    _on_batch_done = batch_processing.on_batch_done

    action_export_text = export_text.action_export_text
    on_ocr_finished = ocr_flow.on_ocr_finished

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MangaOCR App")
        self.settings = QSettings("MangaOCR App")
        self.cache_folder = RecentFolders()
        self.mocr = None
        self.yolo_detector = None
        self.ocr_cache = OCRCache()
        self.ocr_cache._load_cache()
        self.current_preview_idx = None
        self.current_folder = None
        self.entries = []

        self.setDockOptions(QMainWindow.AnimatedDocks)
        self.setDockNestingEnabled(True)

        self._create_widgets()
        self._create_central()
        self._create_statusbar()
        self._create_actions()
        self._create_toolbar()

        try:
            self.restore_window_state()
        except Exception as e:
            self.statusBar().showMessage(f"Ошибка восстановления состояния окна: {e}")

        self.start_models_load()

    def closeEvent(self, event):
        save_window_state(self)
        super().closeEvent(event)

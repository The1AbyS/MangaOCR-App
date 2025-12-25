from PyQt5.QtCore import Qt
from .styles import (btn_add_box_enabled_stylesheet, btn_add_box_disabled_stylesheet,
                    btn_del_box_enabled_stylesheet, btn_del_box_disabled_stylesheet)

def handle_hotkeys(self, event):
    handled = False
    key_text = event.text().lower()

    if key_text in ("о", "j"):
        self.toggle_jardic_browser()
        handled = True

    elif event.key() == Qt.Key_Delete:
        self.delete_selected_image()
        handled = True

    elif key_text in ("a", "ф"):
        if self.add_box_mode:
            self.add_box_mode = False
            self.btn_add_box.setStyleSheet(btn_add_box_disabled_stylesheet)
            self.btn_del_box.setStyleSheet(btn_del_box_disabled_stylesheet)
            self.notification("Режим добавления боксов выключен")
        else:
            self.add_box_mode = True
            self.delete_box_mode = False
            self.btn_add_box.setStyleSheet(btn_add_box_enabled_stylesheet)
            self.btn_del_box.setStyleSheet(btn_del_box_disabled_stylesheet)
            self.notification("Режим добавления боксов включен")
        handled = True

    elif key_text in ("d", "в"):
        if self.delete_box_mode:
            self.delete_box_mode = False
            self.btn_add_box.setStyleSheet(btn_add_box_disabled_stylesheet)
            self.btn_del_box.setStyleSheet(btn_del_box_disabled_stylesheet)
            self.notification("Режим удаления боксов выключен")
        else:
            self.delete_box_mode = True
            self.add_box_mode = False
            self.btn_del_box.setStyleSheet(btn_del_box_enabled_stylesheet)
            self.btn_add_box.setStyleSheet(btn_add_box_disabled_stylesheet)
            self.notification("Режим удаления боксов включен")
        handled = True

    elif event.key() in (Qt.Key_Up,):
        self.show_prev_image()
        handled = True

    elif event.key() in (Qt.Key_Down,):
        self.show_next_image()
        handled = True

    elif key_text in ("q", "й"):
        self.show_prev_image()
        handled = True

    elif key_text in ("e", "у"):
        self.show_next_image()
        handled = True

    elif event.modifiers() == Qt.ControlModifier:
        if key_text in ("o", "щ"):
            self.select_folder()
            handled = True
        elif key_text in ("s", "ы"):
            self.group_content.export_text()
            handled = True
        elif key_text in ("r", "к"):
            self.clear_ocr_cache()
            self.notification("Кэш OCR очищен!")
            handled = True
        elif key_text in ("l", "д"):
            self.clear_images()
            handled = True
        elif key_text in ("z", "я"):
            self.undo_action()
            handled = True

    return handled
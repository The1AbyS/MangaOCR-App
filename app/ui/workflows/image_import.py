import re
from pathlib import Path

from PySide6.QtWidgets import QApplication, QInputDialog

from ...core.parser import ImageParser


def action_parser_from_rawkuma(window, url):
    action_parser(window, text=url)


def clipboard_action(window):
    clipboard = QApplication.clipboard()
    text = clipboard.text().strip()

    if not text:
        window.statusBar().showMessage("Буфер обмена пуст")
        return

    if text.startswith("http://") or text.startswith("https://") or text.startswith("www."):
        window.statusBar().showMessage("Парсинг URL из буфера обмена...")
        try:
            action_parser(window, text=text)
        except Exception as e:
            window.statusBar().showMessage(f"Ошибка парсинга URL: {e}")
        return

    text = re.sub(r"^file:/+", "", text)
    path_clipboard = Path(text)

    if path_clipboard.exists():
        try:
            if path_clipboard.is_dir():
                window.cache_folder.add(path_clipboard)
                window.load_folder(path_clipboard)
        except Exception as e:
            window.statusBar().showMessage(f"Ошибка добавления папки: {e}")
    else:
        window.statusBar().showMessage("Буфер обмена не является ни URL, ни путём")


def action_parser(window, checked=False, text=None):
    if text is None:
        url, ok = QInputDialog.getText(
            window,
            "Загрузить изображения из URL",
            "Введите URL страницы:",
        )
        if not ok or not url.strip():
            return
    else:
        url = text.strip()

    window.thread = ImageParser(url)
    window.thread.progress.connect(window.statusBar().showMessage)
    window.thread.finished.connect(window.on_images_downloaded)
    window.thread.start()


def on_images_downloaded(window, saved_files, out_dir):
    if saved_files and out_dir:
        window.cache_folder.add(Path(out_dir))
        window.load_folder(Path(out_dir))

from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QInputDialog, QListWidgetItem, QMenu
from qt_material_icons import MaterialIcon

from ...core.utils import natural_key
from .operation_progress import show_progress, update_progress


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}


def load_folder(window, folder: Path):
    try:
        folder = Path(folder)
        if not folder or not folder.exists() or not folder.is_dir():
            window.statusBar().showMessage("Папка не существует")
            window.list_widget.clear()
            window.entries = []
            window.current_folder = None
            update_translation_progress(window, -1)
            return

        window.cache_folder.add(folder)
        window.current_folder = folder
    except Exception as e:
        window.statusBar().showMessage(f"Ошибка загрузки папки: {e}")
        window.list_widget.clear()
        window.entries = []
        window.current_folder = None
        return

    window.entries = [
        path for path in sorted(folder.iterdir(), key=lambda x: natural_key(x.name))
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]

    window.list_widget.clear()
    window.dock_list.show()
    for path in window.entries:
        item = QListWidgetItem(path.name)
        item.setData(Qt.UserRole, str(path))
        window.list_widget.addItem(item)

    if window.entries:
        window.list_widget.setCurrentRow(0)

    update_translation_progress(window, window.list_widget.currentRow())


def update_translation_progress(window, current_index=None):
    if current_index is None:
        current_index = window.list_widget.currentRow()
    try:
        window.translation_progress.update_from_cache(
            window.entries,
            getattr(window, "ocr_cache", None),
            current_index,
        )
    except Exception:
        pass


def on_item_clicked(window, item):
    if window.yolo_detector is None:
        window.statusBar().showMessage("Модели ещё не загружены. Пожалуйста, подождите.")
        return

    idx = window.list_widget.row(item)
    if idx < 0 or idx >= len(window.entries):
        return

    path = window.entries[idx]
    window.show_preview(path, boxes=None, reset_zoom=True)

    window.central_stack.setCurrentIndex(1)
    update_translation_progress(window, idx)

    window._current_image_token = object()
    _stop_current_ocr_thread(window)

    if is_cached(window, path=path, idx=idx):
        window.current_preview_idx = idx
        return


    from ...core.ocr import OCRThread

    window.ocr_thread = OCRThread(window, path, token=window._current_image_token)
    show_progress(window, "Подготовка...", 0, 0)
    window.ocr_thread.progress.connect(window.on_ocr_progress)
    window.ocr_thread.finished.connect(window.on_ocr_finished)
    window.ocr_thread.start()

    window.current_preview_idx = idx


def is_cached(window, path, idx):
    if not hasattr(window, "ocr_cache"):
        return

    try:
        cached = window.ocr_cache.get_for_path(path)
    except Exception:
        cached = None

    if cached:
        boxes, frames, md5 = cached
        window.text_boxes, window.frames = boxes, frames
        window.show_preview(path, boxes=window.text_boxes, frames=window.frames, reset_zoom=False)
        window.text_export_panel.set_boxes(window.text_boxes, frames=window.frames, path=window.entries[idx])
        update_translation_progress(window, idx)
        return True

    return False


def _stop_current_ocr_thread(window):
    if hasattr(window, "ocr_thread") and window.ocr_thread is not None:
        window.ocr_thread.quit()
        window.ocr_thread.wait()
        window.ocr_thread = None


def on_ocr_progress(window, value, maximum, token):
    if token is not None and hasattr(window, "_current_image_token") and token != window._current_image_token:
        return
    update_progress(window, value, maximum, f"OCR: {value}/{maximum}")


def next_image(window):
    current_index = window.list_widget.currentRow()
    if current_index < window.list_widget.count() - 1:
        window.list_widget.setCurrentRow(current_index + 1)
        on_item_clicked(window, window.list_widget.currentItem())


def previous_image(window):
    current_index = window.list_widget.currentRow()
    if current_index > 0:
        window.list_widget.setCurrentRow(current_index - 1)
        on_item_clicked(window, window.list_widget.currentItem())


def show_list_menu(window, pos):
    item = window.list_widget.itemAt(pos)
    if item is None:
        return

    idx = window.list_widget.row(item)
    if idx < 0 or idx >= window.list_widget.count():
        return

    path = Path(item.data(Qt.UserRole))

    menu = QMenu()
    open_action = menu.addAction("Открыть как файл")
    open_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))))
    open_action.setIcon(MaterialIcon("image"))

    open_folder_action = menu.addAction("Открыть папку")
    open_folder_action.triggered.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent))))
    open_folder_action.setIcon(MaterialIcon("folder"))

    refresh_action = menu.addAction("Сбросить кэш")
    refresh_action.triggered.connect(lambda: refresh_current(window, path=path))
    refresh_action.setIcon(MaterialIcon("refresh"))

    delete_action = menu.addAction("Удалить из списка")
    delete_action.triggered.connect(lambda: delete_from_list(window, idx=idx))
    delete_action.setIcon(MaterialIcon("delete"))

    menu.addSeparator()

    info_action = menu.addAction("Информация о файле")
    info_action.triggered.connect(lambda: show_file_info(window, path))
    info_action.setIcon(MaterialIcon("info"))

    menu.exec(window.list_widget.viewport().mapToGlobal(pos))


def delete_from_list(window, checked=False, idx=None):
    if idx is None:
        idx = window.list_widget.currentRow()
    if idx < 0 or idx >= window.list_widget.count():
        return

    window.list_widget.takeItem(idx)
    window.entries.pop(idx)

    if idx == getattr(window, "current_preview_idx", None) or window.list_widget.count() == 0:
        window.show_preview(QPixmap())
        window.statusBar().showMessage("")
        window.text_export_panel.set_boxes([], [])
    update_translation_progress(window, window.list_widget.currentRow())


def show_file_info(window, path):
    if not path.exists():
        window.statusBar().showMessage("Файл не найден")
        return

    info = _get_file_info(window, path)
    QInputDialog.getMultiLineText(
        window,
        "Информация о файле",
        "Свойства:",
        info
    )


def refresh_current(window, path=None):
    if path is not None:
        path = Path(path).resolve()
        idx = next(
            (i for i, entry in enumerate(window.entries) if Path(entry).resolve() == path),
            -1,
        )
        if idx >= 0:
            window.list_widget.setCurrentRow(idx)
    else:
        idx = window.list_widget.currentRow()

    if idx < 0:
        return

    path = Path(window.list_widget.item(idx).data(Qt.UserRole))
    path = str(Path(path).resolve())

    window.ocr_cache.clear_current(path)

    orig_path = str(window.entries[idx])
    if orig_path != path:
        window.ocr_cache.clear_current(orig_path)

    window._current_image_token = object()
    window.text_boxes = []
    window.frames = []

    window.show_preview(path)
    window.text_export_panel.set_boxes([], [])
    update_translation_progress(window, idx)
    on_item_clicked(window, window.list_widget.item(idx))


def _get_file_info(window, path: Path) -> str:
    if not path.is_file():
        return "Файл не найден"

    stat = path.stat()
    size_str = _readable_size(stat.st_size)

    with Image.open(path) as img:
        width, height = img.size

    lines = [
        f"{'Имя:'} {path.name}",
        f"{'Размер:'} {size_str} ({stat.st_size:,} байт)",
        f"{'Путь:'} {path.resolve()}",
        f"{'Разрешение:'} {width} × {height} пикс."
    ]

    if hasattr(window, "ocr_cache"):
        try:
            cached = window.ocr_cache.get_for_path(path)
        except Exception:
            cached = None
        if cached:
            boxes, frames, md5 = cached
            lines.append(f"{'Кэш:'} Есть (MD5: {md5})")
            lines.append(f"{' - Боксы:'} {len(boxes)}")
            lines.append(f"{' - Фреймы:'} {len(frames)}")
        else:
            lines.append(f"{'Кэш:'} Нет")

    return "\n".join(lines)


def _readable_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 байт"
    units = ["байт", "КБ", "МБ", "ГБ", "ТБ"]
    index = 0
    size = float(size_bytes)
    while size >= 1024 and index < len(units) - 1:
        size /= 1024
        index += 1
    return f"{size:.1f} {units[index]}" if index > 0 else f"{int(size)} {units[index]}"

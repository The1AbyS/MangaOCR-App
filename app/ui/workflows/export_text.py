from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from ...core.docx_export import export_ocr_cache_to_docx


def action_export_text(window):
    if not hasattr(window, "ocr_cache") or not window.entries:
        window.statusBar().showMessage("Нет текста для экспорта. Сначала обработайте изображения.")
        return

    first_file = Path(window.entries[0])
    default_name = first_file.parent.name + ".docx"
    filename, _ = QFileDialog.getSaveFileName(
        window,
        "Сохранить текст",
        default_name,
        "Word Documents (*.docx)",
    )
    if not filename:
        return

    try:
        export_ocr_cache_to_docx(window.entries, window.ocr_cache, filename)
        window.statusBar().showMessage(f"Текст успешно сохранён в {filename}")
    except Exception as e:
        window.statusBar().showMessage(f"Ошибка сохранения файла: {e}")

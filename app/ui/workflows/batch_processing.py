from PySide6.QtCore import Qt

from ...core.ocr import BatchThread
from .operation_progress import hide_progress, show_progress, update_progress


def action_batch_process(window):
    window.batch_thread = BatchThread(window, window.entries, parent=window)

    window.batch_thread.item_started.connect(window._on_batch_item_started)
    window.batch_thread.item_finished.connect(window._on_batch_item_finished)
    window.batch_thread.stage_changed.connect(window._on_batch_stage_changed)
    window.batch_thread.stage_progress.connect(window._on_batch_stage_progress)
    window.batch_thread.all_done.connect(window._on_batch_done)

    show_progress(window, "Подготовка...", 0, 0)
    window.batch_thread.start()


def on_batch_stage_changed(window, text, maximum):
    show_progress(window, text, 0, maximum)


def on_batch_stage_progress(window, value, maximum, text):
    update_progress(window, value, maximum, text)


def on_batch_item_started(window, idx, path):
    pass


def on_batch_item_finished(window, idx, result):
    if idx == window.list_widget.currentRow():
        boxes, frames = result
        path = window.list_widget.item(idx).data(Qt.UserRole)
        window.text_boxes, window.frames = boxes, frames
        window.text_export_panel.set_boxes(boxes, frames=frames, path=path)
        window.show_preview(
            path,
            boxes=window.text_export_panel._boxes,
            frames=frames,
            reset_zoom=False,
        )


def on_batch_done(window):
    window.update_translation_progress(window.list_widget.currentRow())
    update_progress(window, 1, 1, "Готово")
    hide_progress(window)

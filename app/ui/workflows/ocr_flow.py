from .operation_progress import hide_progress, update_progress


def on_ocr_finished(window, boxes, frames, _img_cv, token):
    if token is not None and hasattr(window, "_current_image_token") and token != window._current_image_token:
        return

    window.text_boxes = boxes
    window.frames = frames
    current_index = window.list_widget.currentRow()
    if current_index < 0 or current_index >= len(window.entries):
        return

    path = window.entries[current_index]

    if hasattr(window, "ocr_cache"):
        try:
            window.ocr_cache.set_for_path(path, boxes, frames)
        except Exception:
            pass

    window.text_export_panel.set_boxes(boxes, frames=frames, path=path)
    window.show_preview(
        path,
        boxes=window.text_export_panel._boxes,
        reset_zoom=False,
        frames=frames,
    )
    window.update_translation_progress(current_index)
    update_progress(window, 1, 1, "Готово")
    hide_progress(window)

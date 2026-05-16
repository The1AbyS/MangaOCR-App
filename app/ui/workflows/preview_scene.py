from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from .preview_overlays import draw_overlays


def show_preview(window, path, boxes=None, frames=None, reset_zoom=False):
    window.preview_view.text_boxes = boxes

    try:
        pixmap_to_show = QPixmap(path) if isinstance(path, QPixmap) else QPixmap(str(path))

        if pixmap_to_show.isNull():
            _clear_scene_pixmap(window)
            _update_project_button_visibility(window)
            return

        _draw_preview_overlays(window, pixmap_to_show, boxes, frames)
        _set_scene_pixmap(window, pixmap_to_show)

        if reset_zoom:
            _reset_zoom(window)

        window.last_pixmap_for_cache = pixmap_to_show
        window.statusBar().showMessage("" if isinstance(path, QPixmap) else str(path))
        _update_project_button_visibility(window)

    except Exception as e:
        window.statusBar().showMessage(f"Ошибка отображения превью: {e}")
        _update_project_button_visibility(window)


def refresh_display_options(window):
    current_index = window.list_widget.currentRow()

    if current_index < 0:
        return

    frames = window.frames if getattr(window, "show_frames", False) else None
    show_preview(
        window,
        window.entries[current_index],
        boxes=getattr(window, "text_boxes", None),
        frames=frames,
    )


def _draw_preview_overlays(window, pixmap_to_show, boxes, frames):
    ordered_boxes = None
    if getattr(window, "show_numbers_boxes", False):
        panel = getattr(window, "text_export_panel", None)
        if panel is not None and hasattr(panel, "_boxes") and panel._boxes:
            ordered_boxes = panel._boxes
        elif boxes:
            ordered_boxes = boxes

    draw_overlays(
        pixmap_to_show,
        boxes=boxes,
        frames=frames,
        show_frames=getattr(window, "show_frames", False),
        show_numbers_boxes=getattr(window, "show_numbers_boxes", False),
        ordered_boxes=ordered_boxes,
    )


def _set_scene_pixmap(window, pixmap_to_show):
    if getattr(window, "current_pixmap_item", None):
        window.current_pixmap_item.setPixmap(pixmap_to_show)
    else:
        window.current_pixmap_item = window.scene.addPixmap(pixmap_to_show)

    try:
        window.scene.setSceneRect(pixmap_to_show.rect())
    except Exception:
        pass


def _clear_scene_pixmap(window):
    if getattr(window, "current_pixmap_item", None) is not None:
        window.scene.removeItem(window.current_pixmap_item)
        window.current_pixmap_item = None
    window.preview_view.text_boxes = []
    window.scene.clear()
    window.last_pixmap_for_cache = None


def _reset_zoom(window):
    try:
        window.preview_view._fit_enabled = True
        window.preview_view._zoom = 1.0
    except Exception:
        pass
    window.preview_view.fitInView(
        window.scene.sceneRect(),
        Qt.KeepAspectRatio
    )


def _update_project_button_visibility(window):
    try:
        window.preview_view.update_project_button_visibility()
    except Exception:
        pass

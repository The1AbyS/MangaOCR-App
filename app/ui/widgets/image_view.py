from types import SimpleNamespace

from PySide6.QtCore import QRect, QRectF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QCursor, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QGraphicsView, QLabel, QToolButton

from ...core.ocr import OCRThread


class ImageView(QGraphicsView):
    PAN_THRESHOLD_SQ = 25
    ZOOM_STEP = 1.1
    MIN_ZOOM = 0.1
    MAX_ZOOM = 10.0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHints(
            self.renderHints()
            | QPainter.Antialiasing
            | QPainter.SmoothPixmapTransform
        )

        self._fit_enabled = True
        self._zoom = 1.0
        self.hand_mode = False
        self.text_boxes = []

        self._left_pressed = False
        self._press_pos = None
        self._last_pan_pos = None
        self._creating_box = False
        self._create_start_scene_pos = None
        self._rubber_rect = None

        self.hovered_text = self._make_overlay_label(
            "background-color: #1e1e1e; color: #eee; padding: 4px; border-radius: 6px;"
        )
        self.copy_feedback = self._make_overlay_label(
            "background-color: #1e1e1e; color: white; padding: 6px; border-radius: 6px;"
        )

        self.project_button = QToolButton(self)
        self.project_button.setText("Проекты")
        self.project_button.setStyleSheet(
            "background-color: rgba(0, 0, 0, 0.6); color: white; padding: 4px; border-radius: 4px;"
        )
        self.project_button.clicked.connect(self.go_to_projects)
        self.project_button.hide()

        self.hover_timer = QTimer(self)
        self.hover_timer.timeout.connect(self.check_hover)
        self.hover_timer.start(30)

        self.setCursor(Qt.ArrowCursor)

    def _make_overlay_label(self, stylesheet):
        label = QLabel(self)
        label.setStyleSheet(stylesheet)
        label.hide()
        return label

    def closeEvent(self, event):
        self.hover_timer.stop()
        super().closeEvent(event)

    def check_hover(self):
        if self.scene() is None or not self.text_boxes:
            self.hovered_text.hide()
            return

        viewport_pos = self.viewport().mapFromGlobal(QCursor.pos())
        scene_pos = self.mapToScene(viewport_pos).toPoint()
        self._show_hover_for_position(viewport_pos, scene_pos)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit_enabled:
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        self.update_project_button_position()

    def update_project_button_position(self):
        margin = 8
        self.project_button.adjustSize()
        self.project_button.move(
            self.width() - self.project_button.width() - margin,
            margin,
        )
        self.project_button.raise_()

    def update_project_button_visibility(self):
        self.project_button.setVisible(self._zoom <= 2.0)
        self.update_project_button_position()

    def go_to_projects(self):
        window = self.window()
        if window is None or not hasattr(window, "central_stack"):
            return

        window.central_stack.setCurrentIndex(0)
        text_export = getattr(window, "text_export_panel", None)
        if text_export is not None:
            text_export.set_boxes([], frames=None, path=None)

    def wheelEvent(self, event):
        self._fit_enabled = False
        requested_factor = self.ZOOM_STEP if event.angleDelta().y() > 0 else 1 / self.ZOOM_STEP
        new_zoom = max(self.MIN_ZOOM, min(self._zoom * requested_factor, self.MAX_ZOOM))
        factor = new_zoom / self._zoom
        self._zoom = new_zoom
        self.scale(factor, factor)
        self.update_project_button_visibility()

    def mouseDoubleClickEvent(self, event):
        self._fit_enabled = True
        self._zoom = 1.0
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        self.update_project_button_visibility()
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint()).toPoint()

        if event.button() == Qt.LeftButton:
            self._left_pressed = True
            self._press_pos = event.position().toPoint()

            if event.modifiers() & Qt.ControlModifier:
                self._handle_ctrl_left_press(scene_pos)
                return

            self._copy_box_text_at(scene_pos)

        elif event.button() == Qt.RightButton:
            self._send_box_text_to_jardic(scene_pos)

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._left_pressed = False

            if self._creating_box:
                self._finish_box_creation(event.position().toPoint())

            if self.hand_mode:
                self.hand_mode = False
                self.setDragMode(QGraphicsView.NoDrag)

            self._update_cursor()

        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        viewport_pos = event.position().toPoint()
        scene_pos = self.mapToScene(viewport_pos).toPoint()

        self._update_pan_state(viewport_pos)
        self._update_rubber_rect(scene_pos)
        self._update_cursor()
        self._show_hover_for_position(viewport_pos, scene_pos)

        super().mouseMoveEvent(event)

    def _handle_ctrl_left_press(self, scene_pos):
        box = self._box_at(scene_pos)
        if box is not None:
            self._delete_box(box)
            return

        self._start_box_creation(scene_pos)

    def _copy_box_text_at(self, scene_pos):
        box = self._box_at(scene_pos)
        if box is None:
            return

        QGuiApplication.clipboard().setText(box.text.strip())
        viewport_pos = self.viewport().mapFromGlobal(QCursor.pos())
        self._show_copy_feedback(viewport_pos)

    def _send_box_text_to_jardic(self, scene_pos):
        box = self._box_at(scene_pos)
        if box is None:
            return

        window = self.window()
        jardic = getattr(window, "jardic_widget", None)
        if jardic is None:
            return

        jardic.send_text_to_jardic(box.text)
        jardic_action = getattr(window, "jardic_act", None)
        if jardic_action is not None:
            jardic_action.setChecked(True)

    def _start_box_creation(self, scene_pos):
        self._creating_box = True
        self._create_start_scene_pos = scene_pos
        self.setCursor(Qt.CrossCursor)

        if self.scene() is None:
            return

        rect = QRectF(scene_pos.x(), scene_pos.y(), 1, 1)
        pen = QPen(QColor(0, 160, 230, 220), 2)
        brush = QBrush(QColor(0, 160, 230, 40))
        self._rubber_rect = self.scene().addRect(rect, pen, brush)

    def _finish_box_creation(self, viewport_pos):
        try:
            rect = self._creation_rect(viewport_pos)
            if rect.width() > 0 and rect.height() > 0:
                box = SimpleNamespace(rect=rect, frame_rect=None, text="")
                self._add_box(box)
                self._start_box_ocr(box)
        finally:
            self._creating_box = False
            self._create_start_scene_pos = None
            self._remove_rubber_rect()

    def _creation_rect(self, viewport_pos):
        start = self._create_start_scene_pos
        end = self.mapToScene(viewport_pos).toPoint()

        x1 = min(start.x(), end.x())
        y1 = min(start.y(), end.y())
        x2 = max(start.x(), end.x())
        y2 = max(start.y(), end.y())
        return QRect(x1, y1, x2 - x1, y2 - y1)

    def _update_pan_state(self, viewport_pos):
        if self._left_pressed and not self.hand_mode and not self._creating_box:
            if self._press_pos is None:
                return
            dx = viewport_pos.x() - self._press_pos.x()
            dy = viewport_pos.y() - self._press_pos.y()
            if dx * dx + dy * dy >= self.PAN_THRESHOLD_SQ:
                self.hand_mode = True
                self._last_pan_pos = viewport_pos

        if not self.hand_mode or self._last_pan_pos is None:
            return

        dx = viewport_pos.x() - self._last_pan_pos.x()
        dy = viewport_pos.y() - self._last_pan_pos.y()
        self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - dx)
        self.verticalScrollBar().setValue(self.verticalScrollBar().value() - dy)
        self._last_pan_pos = viewport_pos

    def _update_rubber_rect(self, scene_pos):
        if (
            not self._creating_box
            or self._rubber_rect is None
            or self._create_start_scene_pos is None
        ):
            return

        start = self._create_start_scene_pos
        x1 = min(start.x(), scene_pos.x())
        y1 = min(start.y(), scene_pos.y())
        x2 = max(start.x(), scene_pos.x())
        y2 = max(start.y(), scene_pos.y())
        self._rubber_rect.setRect(QRectF(x1, y1, x2 - x1, y2 - y1))

    def _remove_rubber_rect(self):
        if self._rubber_rect is not None and self.scene() is not None:
            self.scene().removeItem(self._rubber_rect)
        self._rubber_rect = None

    def _update_cursor(self):
        if self._creating_box:
            self.setCursor(Qt.CrossCursor)
        elif self.hand_mode:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def _box_at(self, scene_pos):
        for box in self.text_boxes or []:
            if box.rect.contains(scene_pos):
                return box
        return None

    def _show_hover_for_position(self, viewport_pos, scene_pos):
        if self.hand_mode or self._creating_box:
            self.hovered_text.hide()
            return

        box = self._box_at(scene_pos)
        if box is None:
            self.hovered_text.hide()
            return

        self.hovered_text.setText(box.text)
        self.hovered_text.adjustSize()
        self.hovered_text.move(viewport_pos.x() + 15, viewport_pos.y() + 15)
        self.hovered_text.show()

    def _show_copy_feedback(self, viewport_pos):
        self.copy_feedback.setText("Скопировано")
        self.copy_feedback.adjustSize()
        self.copy_feedback.move(viewport_pos.x() + 15, viewport_pos.y() + 15)
        self.copy_feedback.show()
        QTimer.singleShot(700, self.copy_feedback.hide)

    def _current_path(self):
        window = self.window()
        if window is None:
            return None

        row = window.list_widget.currentRow()
        if row < 0 or row >= len(window.entries):
            return None
        return window.entries[row]

    def _window_boxes(self):
        window = self.window()
        if window is not None and getattr(window, "text_boxes", None) is not None:
            return window.text_boxes
        return self.text_boxes

    def _set_window_boxes(self, boxes):
        window = self.window()
        if window is not None:
            window.text_boxes = boxes
        self.text_boxes = boxes

    def _add_box(self, box):
        boxes = self._window_boxes()
        boxes.append(box)
        self._set_window_boxes(boxes)
        self._sync_window_preview()

    def _delete_box(self, box):
        boxes = [item for item in self._window_boxes() if item is not box]
        self._set_window_boxes(boxes)
        self._sync_window_preview()

    def _sync_window_preview(self):
        window = self.window()
        path = self._current_path()
        if window is None:
            return

        frames = getattr(window, "frames", None)
        if path is not None and hasattr(window, "ocr_cache"):
            window.ocr_cache.set_for_path(path, window.text_boxes, frames)

        text_export = getattr(window, "text_export_panel", None)
        if text_export is not None:
            text_export.set_boxes(window.text_boxes, frames=frames, path=path)

        if path is not None:
            window.show_preview(path, boxes=window.text_boxes, frames=frames, reset_zoom=False)

    def _start_box_ocr(self, box):
        window = self.window()
        pixmap = getattr(window, "last_pixmap_for_cache", None)
        if window is None or pixmap is None:
            return

        item = SimpleNamespace(pixmap=pixmap, boxes=[box])
        thread = OCRThread(window, item)
        thread.finished.connect(lambda boxes, frames, img, token: self._on_box_ocr_finished(box, boxes))
        thread.finished.connect(lambda *args, thread=thread: self._cleanup_ocr_thread(thread))

        if not hasattr(window, "_active_ocr_threads"):
            window._active_ocr_threads = []
        window._active_ocr_threads.append(thread)
        thread.start()

    def _on_box_ocr_finished(self, original_box, boxes):
        if boxes:
            original_box.text = boxes[0].text
        self._sync_window_preview()

    def _cleanup_ocr_thread(self, thread):
        window = self.window()
        if window is not None and hasattr(window, "_active_ocr_threads"):
            try:
                window._active_ocr_threads.remove(thread)
            except ValueError:
                pass
        thread.deleteLater()

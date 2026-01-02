from PySide6.QtWidgets import QGraphicsView, QLabel
from PySide6.QtCore import Qt, QTimer, QRect, QRectF
from PySide6.QtGui import QPainter, QCursor, QGuiApplication, QPen, QColor
from PySide6.QtGui import QBrush
from ..core.ocr import OCRThread
from ..core.utils import pixmap_to_cv
from PIL import Image
import cv2

class ImageView(QGraphicsView):
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

        self.hover_timer = QTimer()
        self.hover_timer.timeout.connect(self.check_hover)
        self.hover_timer.start(30)
        self.hover_timer.setParent(self)

        self.hand_mode = False
        self.text_boxes = [] 
        self._creating_box = False
        self._create_start_scene_pos = None
        self._rubber_rect = None
        self.hovered_text = QLabel(self)
        self.hovered_text.setStyleSheet(
            "background-color: #1e1e1e; color: #eee; padding: 4px; border-radius: 6px;"
        )
        self.hovered_text.hide()
        self.copy_feedback = QLabel(self)
        self.copy_feedback.setStyleSheet(
            "background-color: #1e1e1e; color: white; padding: 6px; border-radius: 6px;"
        )
        self.copy_feedback.hide()
        self._left_pressed = False
        self._press_pos = None
        self._last_pan_pos = None
        self.setCursor(Qt.ArrowCursor)

    def closeEvent(self, event):
        self.hover_timer.stop()
        super().closeEvent(event)

    def check_hover(self):
        if self.scene() is None or not self.text_boxes:
            return

        vp_pos = self.viewport().mapFromGlobal(QCursor.pos())
        scene_pos = self.mapToScene(vp_pos)

        hovered = False
        for box in self.text_boxes:
            if box.rect.contains(scene_pos.toPoint()):
                self.hovered_text.setText(box.text)
                self.hovered_text.adjustSize()
                x = vp_pos.x() + 15
                y = vp_pos.y() + 15
                self.hovered_text.move(int(x), int(y))
                self.hovered_text.show()
                hovered = True
                break

        if not hovered:
            self.hovered_text.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._fit_enabled:
            self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)

    def wheelEvent(self, event):
        self._fit_enabled = False
        zoom_factor = 1.1
        if event.angleDelta().y() > 0:
            factor = zoom_factor
            self._zoom *= zoom_factor
        else:
            factor = 1 / zoom_factor
            self._zoom /= zoom_factor
        self._zoom = max(0.1, min(self._zoom, 10.0))
        self.scale(factor, factor)

    def mouseDoubleClickEvent(self, event):
        self._fit_enabled = True
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._left_pressed = True
            self._press_pos = event.position().toPoint()

            scene_pos = self.mapToScene(self._press_pos)
            ctrl = bool(event.modifiers() & Qt.ControlModifier)

            if ctrl:
                for box in list(self.text_boxes):
                    if box.rect.contains(scene_pos.toPoint()):
                        wnd = self.window()
                        try:
                            if hasattr(wnd, 'text_boxes') and wnd.text_boxes is not None:
                                wnd.text_boxes = [b for b in wnd.text_boxes if b is not box]
                                self.text_boxes = wnd.text_boxes
                            else:
                                self.text_boxes = [b for b in self.text_boxes if b is not box]

                            path = None
                            try:
                                path = wnd.entries[wnd.list_widget.currentRow()]
                            except Exception:
                                path = None

                            if path is not None and hasattr(wnd, 'ocr_cache'):
                                try:
                                    wnd.ocr_cache.set_for_path(path, wnd.text_boxes, getattr(wnd, 'frames', None))
                                except Exception:
                                    pass

                            try:
                                wnd.text_export_panel.set_boxes(wnd.text_boxes, frames=getattr(wnd, 'frames', None), path=path)
                            except Exception:
                                pass

                            if path is not None:
                                try:
                                    wnd.show_preview(path, boxes=wnd.text_boxes, frames=getattr(wnd, 'frames', None), reset_zoom=False)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        break

                else:
                    self._creating_box = True
                    self._create_start_scene_pos = scene_pos.toPoint()
                    self.setCursor(Qt.CrossCursor)
                    try:
                        if self.scene() is not None:
                            start = self._create_start_scene_pos
                            r = QRectF(start.x(), start.y(), 1, 1)
                            pen = QPen(QColor(0, 160, 230, 220), 2)
                            brush = QBrush(QColor(0, 160, 230, 40))
                            self._rubber_rect = self.scene().addRect(r, pen, brush)
                    except Exception:
                        self._rubber_rect = None
                return

            for box in self.text_boxes:
                if box.rect.contains(scene_pos.toPoint()):
                    QGuiApplication.clipboard().setText(box.text.strip())
                    try:
                        vp_pos = self.viewport().mapFromGlobal(QCursor.pos())
                        self.copy_feedback.setText("Скопировано")
                        self.copy_feedback.adjustSize()
                        x = vp_pos.x() + 15
                        y = vp_pos.y() + 15
                        self.copy_feedback.move(int(x), int(y))
                        self.copy_feedback.show()
                        QTimer.singleShot(700, lambda: self.copy_feedback.hide())
                    except Exception:
                        pass
                    break
        elif event.button() == Qt.RightButton:
            scene_pos = self.mapToScene(event.position().toPoint())
            for box in self.text_boxes:
                if box.rect.contains(scene_pos.toPoint()):
                    wnd = self.window()
                    jard = getattr(wnd, 'jardic_widget', None)
                    if jard is not None:
                        try:
                            jard.send_text_to_jardic(box.text)
                            act = getattr(wnd, 'jardic_act', None)
                            if act is not None:
                                try:
                                    act.setChecked(True)
                                except Exception:
                                    pass
                        except Exception:
                            pass
                    break

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._left_pressed = False

            if self._creating_box:
                try:
                    start = self._create_start_scene_pos
                    end = self.mapToScene(event.position().toPoint()).toPoint()
                    x1 = min(start.x(), end.x())
                    y1 = min(start.y(), end.y())
                    x2 = max(start.x(), end.x())
                    y2 = max(start.y(), end.y())
                    rect = QRect(x1, y1, x2 - x1, y2 - y1)
                    if rect.width() > 0 and rect.height() > 0:
                        obj = type('BoxOrFrame', (), {})()
                        obj.rect = rect
                        obj.frame_rect = None
                        obj.text = ""

                        wnd = self.window()
                        pixmap = getattr(wnd, 'last_pixmap_for_cache', None)
                        if pixmap is not None:
                            try:
                                img_cv = pixmap_to_cv(pixmap)
                                x, y, w, h = rect.getRect()[0:4]
                                x, y = max(0, x), max(0, y)
                                w, h = min(w, img_cv.shape[1] - x), min(h, img_cv.shape[0] - y)
                                if w > 0 and h > 0:
                                    crop = img_cv[y:y+h, x:x+w]
                                    try:
                                        pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                                        obj.text = ""
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                        try:
                            if hasattr(wnd, 'text_boxes') and wnd.text_boxes is not None:
                                wnd.text_boxes.append(obj)
                                self.text_boxes = wnd.text_boxes
                            else:
                                self.text_boxes.append(obj)
                            path = None
                            try:
                                path = wnd.entries[wnd.list_widget.currentRow()]
                            except Exception:
                                path = None

                            if path is not None and hasattr(wnd, 'ocr_cache'):
                                try:
                                    wnd.ocr_cache.set_for_path(path, wnd.text_boxes, getattr(wnd, 'frames', None))
                                except Exception:
                                    pass

                            try:
                                wnd.text_export_panel.set_boxes(wnd.text_boxes, frames=getattr(wnd, 'frames', None), path=path)
                            except Exception:
                                pass

                            if path is not None:
                                try:
                                    wnd.show_preview(path, boxes=wnd.text_boxes, frames=getattr(wnd, 'frames', None), reset_zoom=False)
                                except Exception:
                                    pass

                            try:
                                item = type('ImageItem', (), {})()
                                item.pixmap = getattr(wnd, 'last_pixmap_for_cache', None)
                                item.boxes = [obj]
                                thr = OCRThread(wnd, item)

                                def _on_finished(boxes, frames, img, token):
                                    try:
                                        if boxes and len(boxes) > 0:
                                            new_text = boxes[0].text
                                            for b in wnd.text_boxes:
                                                try:
                                                    if b is obj or (hasattr(b, 'rect') and b.rect == obj.rect):
                                                        b.text = new_text
                                                        break
                                                except Exception:
                                                    pass

                                        try:
                                            if path is not None and hasattr(wnd, 'ocr_cache'):
                                                wnd.ocr_cache.set_for_path(path, wnd.text_boxes, getattr(wnd, 'frames', None))
                                        except Exception:
                                            pass
                                        try:
                                            wnd.text_export_panel.set_boxes(wnd.text_boxes, frames=getattr(wnd, 'frames', None), path=path)
                                        except Exception:
                                            pass
                                        try:
                                            if path is not None:
                                                wnd.show_preview(path, boxes=wnd.text_boxes, frames=getattr(wnd, 'frames', None), reset_zoom=False)
                                        except Exception:
                                            pass
                                    except Exception:
                                        pass

                                thr.finished.connect(_on_finished)
                                try:
                                    if not hasattr(wnd, '_active_ocr_threads'):
                                        wnd._active_ocr_threads = []
                                    wnd._active_ocr_threads.append(thr)
                                except Exception:
                                    pass

                                def _cleanup_thread():
                                    try:
                                        if hasattr(wnd, '_active_ocr_threads') and thr in wnd._active_ocr_threads:
                                            wnd._active_ocr_threads.remove(thr)
                                    except Exception:
                                        pass
                                    try:
                                        thr.deleteLater()
                                    except Exception:
                                        pass

                                thr.finished.connect(_cleanup_thread)
                                thr.start()
                            except Exception:
                                pass
                        except Exception:
                            pass

                except Exception:
                    pass

                self._creating_box = False
                self._create_start_scene_pos = None
                try:
                    if self._rubber_rect is not None and self.scene() is not None:
                        try:
                            self.scene().removeItem(self._rubber_rect)
                        except Exception:
                            pass
                        self._rubber_rect = None
                except Exception:
                    pass

                self.setCursor(Qt.ArrowCursor)
            if self.hand_mode:
                self.hand_mode = False
                self.setCursor(Qt.ArrowCursor)
                self.setDragMode(QGraphicsView.NoDrag)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())
        try:
            if self._left_pressed and not self.hand_mode and not self._creating_box:
                cur = event.position().toPoint()
                if self._press_pos is not None:
                    dx = cur.x() - self._press_pos.x()
                    dy = cur.y() - self._press_pos.y()
                    if (dx*dx + dy*dy) >= 25: 
                        self.hand_mode = True
                        self._last_pan_pos = cur
                        self.setCursor(Qt.PointingHandCursor)

                    pass

            if self.hand_mode and self._last_pan_pos is not None:
                cur = event.position().toPoint()
                dx = cur.x() - self._last_pan_pos.x()
                dy = cur.y() - self._last_pan_pos.y()
                try:
                    hbar = self.horizontalScrollBar()
                    vbar = self.verticalScrollBar()
                    hbar.setValue(hbar.value() - dx)
                    vbar.setValue(vbar.value() - dy)
                except Exception:
                    pass
                self._last_pan_pos = cur
        except Exception:
            pass

        if self._creating_box and self._rubber_rect is not None and self._create_start_scene_pos is not None:
            try:
                start = self._create_start_scene_pos
                curp = scene_pos.toPoint()
                x1 = min(start.x(), curp.x())
                y1 = min(start.y(), curp.y())
                x2 = max(start.x(), curp.x())
                y2 = max(start.y(), curp.y())
                rectf = QRectF(x1, y1, x2 - x1, y2 - y1)
                self._rubber_rect.setRect(rectf)
            except Exception:
                pass

        if self.hand_mode:
            self.setCursor(Qt.PointingHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

        hovered = False
        for box in self.text_boxes:
            if box.rect.contains(scene_pos.toPoint()):
                self.hovered_text.setText(box.text)
                self.hovered_text.adjustSize()
                vp_pos = event.position().toPoint()
                x = vp_pos.x() + 15
                y = vp_pos.y() + 15
                self.hovered_text.move(int(x), int(y))
                self.hovered_text.show()
                hovered = True
                break

        if not hovered:
            self.hovered_text.hide()

        super().mouseMoveEvent(event)

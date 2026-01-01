from PySide6.QtWidgets import QGraphicsView, QLabel
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QCursor, QGuiApplication

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
            if self.hand_mode:
                self.hand_mode = False
                self.setCursor(Qt.ArrowCursor)
                self.setDragMode(QGraphicsView.NoDrag)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())
        try:
            if self._left_pressed and not self.hand_mode:
                cur = event.position().toPoint()
                if self._press_pos is not None:
                    dx = cur.x() - self._press_pos.x()
                    dy = cur.y() - self._press_pos.y()
                    if (dx*dx + dy*dy) >= 25: 
                        self.hand_mode = True
                        self._last_pan_pos = cur
                        self.setCursor(Qt.PointingHandCursor)

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

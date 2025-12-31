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

        self.hand_mode = False
        self.text_boxes = [] 
        self.hovered_text = QLabel(self)
        self.hovered_text.setStyleSheet("background-color: rgba(255,255,255,200); padding: 2px;")
        self.hovered_text.hide()
        self.setCursor(Qt.ArrowCursor)

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
            self.hand_mode = False
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self.setCursor(Qt.PointingHandCursor)

            scene_pos = self.mapToScene(event.position().toPoint())
            for box in self.text_boxes:
                if box.rect.contains(scene_pos.toPoint()):
                    QGuiApplication.clipboard().setText(box.text.strip())
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
                        except Exception:
                            pass
                    break

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.hand_mode = False
            self.setCursor(Qt.ArrowCursor)
            self.setDragMode(QGraphicsView.NoDrag)
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.position().toPoint())

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

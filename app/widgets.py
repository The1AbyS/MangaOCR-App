from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.setFixedHeight(40)

        self.title_label = QLabel("MangaOCR App")
        self.title_label.setStyleSheet("""
            font-weight: 700;
            font-size: 16px;
            color: #f0f0f0;
            padding-left: 10px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: transparent;
        """)

        self.btn_minimize = QPushButton("—")
        self.btn_close = QPushButton("✕")

        for btn in (self.btn_minimize, self.btn_close):
            btn.setFixedSize(40, 28)

        self.btn_minimize.clicked.connect(self.on_minimize)
        self.btn_close.clicked.connect(self.on_close)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_close)

        self._start_pos = None

    def paintEvent(self, event):
        pass

    def on_minimize(self):
        self.parent.showMinimized()

    def on_close(self):
        self.parent.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self._start_pos:
            delta = event.globalPos() - self._start_pos
            self.parent.move(self.parent.pos() + delta)
            self._start_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self._start_pos = None

class SmoothListWidget(QListWidget):
    def wheelEvent(self, event):
        scroll_bar = self.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.value() - event.angleDelta().y() // 8)
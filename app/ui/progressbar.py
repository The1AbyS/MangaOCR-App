from PySide6.QtWidgets import QProgressBar, QWidget, QHBoxLayout
from PySide6.QtCore import Qt

class OCRProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedWidth(200)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        layout.addWidget(self.progress_bar)

    def set_value(self, value: int, maximum: int = None):
        if maximum is not None and maximum > 0:
            self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)
    
    def reset(self):
        self.progress_bar.setValue(0)

    def show_bar(self):
        self.progress_bar.setVisible(True)

    def hide_bar(self):
        self.progress_bar.setVisible(False)

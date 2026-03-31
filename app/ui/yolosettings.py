from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSlider, QPushButton, QGroupBox
from PySide6.QtCore import Qt, Signal


class YoloSettingsWidget(QWidget):

    settings_changed = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setMinimumWidth(300)

        self.default_values = {"conf": 0.25, "iou": 0.45, "imgsz": 640}

        self._build_ui()
        self._connect_signals()
        self.emit_settings()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)

        group = QGroupBox("")
        layout = QVBoxLayout()

        self.conf_label = QLabel()
        self.conf_slider = QSlider(Qt.Horizontal)
        self.conf_slider.setRange(0, 100)
        self.conf_slider.setValue(int(self.default_values["conf"] * 100))

        self.iou_label = QLabel()
        self.iou_slider = QSlider(Qt.Horizontal)
        self.iou_slider.setRange(0, 100)
        self.iou_slider.setValue(int(self.default_values["iou"] * 100))

        self.imgsz_label = QLabel()
        self.imgsz_slider = QSlider(Qt.Horizontal)
        self.imgsz_slider.setRange(320, 1920)
        self.imgsz_slider.setValue(self.default_values["imgsz"])

        self.apply = QPushButton("Применить")

        layout.addWidget(self.conf_label)
        layout.addWidget(self.conf_slider)

        layout.addWidget(self.iou_label)
        layout.addWidget(self.iou_slider)

        layout.addWidget(self.imgsz_label)
        layout.addWidget(self.imgsz_slider)

        layout.addWidget(self.apply)

        group.setLayout(layout)
        main_layout.addWidget(group)

        self._update_all_labels()

    def _connect_signals(self):
        self.conf_slider.valueChanged.connect(self._update_all_labels)
        self.iou_slider.valueChanged.connect(self._update_all_labels)
        self.imgsz_slider.valueChanged.connect(self._update_all_labels)
        self.apply.clicked.connect(self.apply_clicked)

    def _update_all_labels(self):
        self.conf_label.setText(f"Confidence: {self.conf_slider.value() / 100:.2f}")
        self.iou_label.setText(f"IoU: {self.iou_slider.value() / 100:.2f}")
        self.imgsz_label.setText(f"Image size: {self.imgsz_slider.value()}")

    def get_settings(self):
        return {"conf": self.conf_slider.value() / 100,
                "iou": self.iou_slider.value() / 100,
                "imgsz": self.imgsz_slider.value()}

    def apply_clicked(self):
        self.emit_settings()

    def emit_settings(self):
        self.settings_changed.emit(self.get_settings())
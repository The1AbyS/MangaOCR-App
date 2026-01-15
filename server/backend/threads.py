import os
import sys
from pathlib import Path
from manga_ocr import MangaOcr
from ultralytics import YOLO
import numpy as np
from PIL import Image
from PySide6.QtCore import QThread, Signal

def resource_path(relative_path):
    if hasattr(sys, '_internal'):
        return os.path.join(sys._internal, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)

class ModelsLoadThread(QThread):
    finished = Signal(object, object) 
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            model_dir = resource_path(Path("..", "..", "models", "model_manga_ocr"))
            mocr = MangaOcr(pretrained_model_name_or_path=model_dir)

            yolo_model_path = resource_path(Path("..", "..", "models", "yolo_m.pt"))
            yolo = YOLO(yolo_model_path)

            try:
                dummy_img = np.zeros((64, 64, 3), dtype=np.uint8)
                _ = yolo(dummy_img)
            except Exception:
                pass

            try:
                dummy_pil = Image.new('RGB', (16, 16))
                try:
                    _ = mocr(dummy_pil)
                except Exception:
                    pass
            except Exception:
                pass
            self.finished.emit(mocr, yolo)

        except Exception as e:
            self.error.emit(str(e))
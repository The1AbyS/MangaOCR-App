import os
import sys
from PyQt5.QtCore import QThread, pyqtSignal

def resource_path(relative_path):
    if hasattr(sys, '_internal'):
        return os.path.join(sys._internal, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)

class ModelLoadThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, load_func, parent=None):
        super().__init__(parent)
        self.load_func = load_func

    def run(self):
        try:
            model = self.load_func()
            self.finished.emit(model)
        except Exception as e:
            self.error.emit(str(e))
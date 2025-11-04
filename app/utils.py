import re
import cv2
import numpy as np
from PyQt5.QtGui import QImage

def natural_key(string):
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', string)]

def pixmap_to_cv(pixmap):
    qimg = pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
    width, height = qimg.width(), qimg.height()
    ptr = qimg.bits()
    ptr.setsize(qimg.byteCount())
    bytes_per_line = qimg.bytesPerLine()
    arr = np.frombuffer(ptr, np.uint8).reshape((height, bytes_per_line))
    arr = arr[:, :width*3].reshape((height, width, 3))
    return cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
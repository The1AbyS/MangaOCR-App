from PyQt5.QtCore import QByteArray, QBuffer
from PyQt5.QtGui import QPixmap
import hashlib

class OCRCache:
    def __init__(self):
        self.cache = {}

    def get(self, key):
        """Получить результат OCR из кэша"""
        return self.cache.get(key)

    def set(self, key, value):
        """Сохранить результат OCR в кэш"""
        self.cache[key] = value

    def clear(self):
        """Очистить кэш"""
        self.cache.clear()

    def __contains__(self, key):
        return key in self.cache

    def __getitem__(self, key):
        return self.cache[key]

    def __setitem__(self, key, value):
        self.cache[key] = value

def pixmap_md5(pixmap):
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QBuffer.WriteOnly)
    pixmap.save(buffer, "PNG")
    md5 = hashlib.md5(bytes(ba)).hexdigest()
    return md5
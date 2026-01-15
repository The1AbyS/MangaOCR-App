from PySide6.QtCore import QByteArray, QBuffer
from PySide6.QtGui import QPixmap
import hashlib
from pathlib import Path

class OCRCache:
    def __init__(self):
        self.cache = {}
        self.path_map = {}

    def clear(self):
        self.cache.clear()
        self.path_map.clear()

    def set_by_md5(self, md5, boxes, frames):
        if not md5:
            return
        self.cache[md5] = (boxes, frames, md5)

    def get_by_md5(self, md5):
        return self.cache.get(md5)

    def has_md5(self, md5):
        return md5 in self.cache

    def set_for_path(self, path, boxes, frames):
        try:
            md5 = md5_from_path(path)
        except Exception:
            md5 = None
        if md5:
            self.set_by_md5(md5, boxes, frames)
            self.path_map[str(path)] = md5

    def get_for_path(self, path):
        try:
            md5 = md5_from_path(path)
        except Exception:
            md5 = None
        if not md5:
            return None
        return self.get_by_md5(md5)

    def set_for_pixmap(self, pixmap, boxes, frames):
        md5 = pixmap_md5(pixmap)
        if md5:
            self.set_by_md5(md5, boxes, frames)

    def get_for_pixmap(self, pixmap):
        md5 = pixmap_md5(pixmap)
        if not md5:
            return None
        return self.get_by_md5(md5)

    def __contains__(self, key):
        if not key:
            return False
        if isinstance(key, str) and len(key) == 32 and all(c in "0123456789abcdef" for c in key.lower()):
            return key in self.cache
        return str(key) in self.path_map and self.path_map[str(key)] in self.cache

    def __getitem__(self, key):
        if isinstance(key, str) and len(key) == 32 and all(c in "0123456789abcdef" for c in key.lower()):
            return self.get_by_md5(key)
        path = str(key)
        md5 = self.path_map.get(path)
        if md5:
            return self.get_by_md5(md5)
        try:
            md5 = md5_from_path(path)
        except Exception:
            md5 = None
        if md5:
            return self.get_by_md5(md5)
        raise KeyError(key)

    def __setitem__(self, key, value):
        if isinstance(value, tuple) and len(value) >= 2:
            boxes, frames = value[0], value[1]
        else:
            raise ValueError("value must be (boxes, frames[, md5])")
        if isinstance(key, str) and len(key) == 32 and all(c in "0123456789abcdef" for c in key.lower()):
            self.set_by_md5(key, boxes, frames)
            return
        path = str(key)
        try:
            md5 = md5_from_path(path)
        except Exception:
            md5 = None
        if md5:
            self.set_by_md5(md5, boxes, frames)
            self.path_map[path] = md5
        else:
            raise ValueError("Could not compute md5 for key")

def pixmap_md5(pixmap):
    if pixmap is None:
        return None
    if not isinstance(pixmap, QPixmap):
        try:
            pixmap = QPixmap(pixmap)
        except Exception:
            return None
    ba = QByteArray()
    buffer = QBuffer(ba)
    if not buffer.open(QBuffer.WriteOnly):
        return None
    try:
        ok = pixmap.save(buffer, "PNG")
        if not ok:
            return None
        data = ba.data()
        if isinstance(data, memoryview):
            data = data.tobytes()
        return hashlib.md5(data).hexdigest()
    finally:
        buffer.close()

def md5_from_path(path):
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(path)
    h = hashlib.md5()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
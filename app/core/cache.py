from PySide6.QtCore import QByteArray, QBuffer, QRect
from PySide6.QtGui import QPixmap
import hashlib
import re
from pathlib import Path

from flask import json
from tomlkit import item

class OCRCache:
    def __init__(self, cache_file=None):
        self.cache = {}
        self.path_map = {}

        self.cache_file = cache_file or Path.home() / ".mangaocr_cache.json"

    def clear(self):
        self.cache.clear()
        self.path_map.clear()

    def clear_current(self, path):
        md5 = self.path_map.get(path)
        if not md5:
            return False

        if md5 in self.cache:
            del self.cache[md5]

        del self.path_map[path]
        return True

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
        try:
            self._add_cache(path, boxes, frames, md5)
        except:
            pass
        
    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                data = []
                for md5, (boxes, frames, _) in self.cache.items():
                    path = None
                    for p, m in self.path_map.items():
                        if m == md5:
                            path = p
                            break
                    data.append({
                        "md5": md5,
                        "boxes": [box_to_dict(b) for b in boxes],
                        "frames": [box_to_dict(f) for f in frames],
                        "path": path
                    })
                json.dump(data, f, ensure_ascii=False, indent=2, cls=CompactEncoder)
        except Exception as e:
            print(e)

    def _add_cache(self, path: Path, boxes, frames, md5=None):
        if not md5 and path:
            try:
                md5 = md5_from_path(path)
            except Exception:
                md5 = None
        if not md5:
            return
        self.cache[md5] = (boxes, frames, md5)
        if path:
            self.path_map[str(path)] = md5
        self._save_cache()

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for item in data:
                        md5 = item.get("md5")
                        boxes = [box_from_dict(b) for b in item.get("boxes", [])]
                        frames = [box_from_dict(f) for f in item.get("frames", [])]
                        path = item.get("path")
                        if md5 and boxes is not None and frames is not None:
                            self.cache[md5] = (boxes, frames, md5)
                            if path:
                                self.path_map[path] = md5
            except Exception as e:
                print(e)

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

def box_to_dict(box):
    rect = getattr(box, "rect", None)
    frame_rect = getattr(box, "frame_rect", None)
    text = getattr(box, "text", "")
    
    return {
        "rect": [rect.x(), rect.y(), rect.width(), rect.height()] if rect else None,
        "frame_rect": [frame_rect.x(), frame_rect.y(), frame_rect.width(), frame_rect.height()] if frame_rect else None,
        "text": text
    }

def box_from_dict(d):
    obj = type('BoxOrFrame', (), {})()
    
    if d.get("rect"):
        x, y, w, h = d["rect"]
        obj.rect = QRect(x, y, w, h)
    else:
        obj.rect = None
    
    if d.get("frame_rect"):
        x, y, w, h = d["frame_rect"]
        obj.frame_rect = QRect(x, y, w, h)
    else:
        obj.frame_rect = None

    obj.text = d.get("text", "")
    return obj

class CompactEncoder(json.JSONEncoder):
    def iterencode(self, obj, _one_shot=False):
        chunks = super().iterencode(obj, _one_shot)
        text = ''.join(chunks)
        text = re.sub(
            r'\[\s*([0-9,\s]+)\s*\]',
            lambda m: '[' + ', '.join(s.strip() for s in m.group(1).split(',')) + ']',
            text
        )
        return [text]
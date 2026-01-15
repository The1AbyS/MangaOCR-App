from PySide6.QtCore import QThread, Signal, QRect
from .utils import MangaTextBox, pixmap_to_cv
from .cache import pixmap_md5
from pathlib import Path
import os
import cv2
import numpy as np
from PIL import Image

class OCRThread(QThread):
    finished = Signal(list, list, object, object)
    progress = Signal(int, int, object)

    def __init__(self, app_ref, image_item, token=None):
        super().__init__()
        self.app_ref = app_ref
        self.image_item = image_item
        self.token = token
        
    def run(self):
        items = self.image_item

        if not isinstance(items, (list, tuple)):
            items = [items]

        for image_item in items:
            self._process_ocr(image_item)

    def _process_ocr(self, image_item):
        provided_boxes = getattr(image_item, 'boxes', None) or getattr(image_item, 'provided_boxes', None)

        if provided_boxes is None and hasattr(self.app_ref, 'ocr_cache'):
            try:
                if isinstance(image_item, Path):
                    cached = self.app_ref.ocr_cache.get_for_path(image_item)
                    if cached:
                        boxes, frames, md5 = cached
                        self.finished.emit(boxes, frames, None, self.token)
                        return
                else:
                    pix = getattr(image_item, 'pixmap', None)
                    if pix is not None:
                        cached = self.app_ref.ocr_cache.get_for_pixmap(pix)
                        if cached:
                            boxes, frames, md5 = cached
                            self.finished.emit(boxes, frames, None, self.token)
                            return
            except Exception:
                pass

        img_cv = None
        if isinstance(image_item, Path):
            img_cv = self.imread_unicode(image_item)
        elif hasattr(image_item, 'pixmap') and image_item.pixmap:
            img_cv = pixmap_to_cv(image_item.pixmap)

        if img_cv is None:
            self.finished.emit([], [], None, self.token)
            return

        if provided_boxes is not None:
            boxes = provided_boxes
            frames = getattr(image_item, 'frames', []) or []
        else:
            boxes, frames = self.detect_text_boxes(img_cv)
        total = len(boxes)
        h_img, w_img = img_cv.shape[:2]

        for idx, box in enumerate(boxes):
            x, y, w, h = box.rect.getRect()[0:4] 
            x, y = max(0, x), max(0, y)
            w, h = min(w, w_img - x), min(h, h_img - y)
            if w <= 0 or h <= 0:
                continue

            crop_img = img_cv[y:y+h, x:x+w]
            if crop_img is None or crop_img.size == 0:
                continue

            try:
                pil_img = Image.fromarray(cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB))
            except Exception:
                continue

            mocr_callable = getattr(self.app_ref, 'mocr', None)
            if callable(mocr_callable):
                try:
                    text = mocr_callable(pil_img)
                except Exception:
                    text = ""
            else:
                text = ""
            box.text = text

            self.progress.emit(idx + 1, total, self.token)

        if hasattr(self.app_ref, 'ocr_cache'):
            try:
                if isinstance(self.image_item, Path):
                    self.app_ref.ocr_cache.set_for_path(self.image_item, boxes, frames)
                else:
                    pix = getattr(image_item, 'pixmap', None)
                    if pix is not None:
                        self.app_ref.ocr_cache.set_for_pixmap(pix, boxes, frames)
            except Exception:
                pass

        self.finished.emit(boxes, frames, img_cv, self.token)

    def imread_unicode(self, path):
        with open(path, 'rb') as f:
            data = f.read()
        img_array = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img

    def detect_text_boxes(self, image_cv):
        boxes = []
        frames = []

        yolo_detector = getattr(self.app_ref, 'yolo_detector', None)
        if yolo_detector is not None:
            results = yolo_detector(image_cv, conf=0.25, iou=0.45)

            for r in results[0].boxes:
                cls = int(r.cls[0])
                x1, y1, x2, y2 = map(int, r.xyxy[0].cpu().numpy())
                rect = QRect(x1, y1, x2 - x1, y2 - y1)

                obj = type('BoxOrFrame', (), {})()
                obj.rect = rect
                obj.text = "" 

                if cls == 3:
                    obj.frame_rect = None  
                    boxes.append(obj)
                elif cls == 2:
                    frames.append(obj)

        return boxes, frames
    
class BatchThread(QThread):
    item_started = Signal(int, object)
    item_finished = Signal(int, object)
    all_done = Signal()

    def __init__(self, app_ref, entries, parent=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.entries = entries

    def run(self):
        for idx, path in enumerate(self.entries):
            self.item_started.emit(idx, path)

            ocr_thread = OCRThread(self.app_ref, path)
            result_container = []

            def on_finished(boxes, frames, img, token):
                result_container.append((boxes, frames))

            ocr_thread.finished.connect(on_finished)
            ocr_thread.run() 
            self.item_finished.emit(idx, result_container[0])

        self.all_done.emit()
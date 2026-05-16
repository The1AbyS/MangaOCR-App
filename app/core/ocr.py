from PySide6.QtCore import QThread, Signal, QRect
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

from .utils import pixmap_to_cv

class OCRProcessor:
    def __init__(self, app_ref, image_item, token=None):
        self.app_ref = app_ref
        self.image_item = image_item
        self.token = token

    def process(self, progress_callback=None):
        results = []
        items = self.image_item

        if not isinstance(items, (list, tuple)):
            items = [items]

        for image_item in items:
            results.append(self._process_ocr(image_item, progress_callback))
        return results

    def _process_ocr(self, image_item, progress_callback=None):
        provided_boxes = getattr(image_item, 'boxes', None) or getattr(image_item, 'provided_boxes', None)

        if provided_boxes is None:
            cached = self.get_cached(image_item)
            if cached:
                boxes, frames, _md5 = cached
                return boxes, frames, None

        img_cv = self.load_image(image_item)

        if img_cv is None:
            return [], [], None

        if provided_boxes is not None:
            boxes = provided_boxes
            frames = getattr(image_item, 'frames', []) or []
        else:
            boxes, frames = self.detect_text_boxes(img_cv)
        self.recognize_boxes(image_item, img_cv, boxes, frames, progress_callback)

        return boxes, frames, img_cv

    def get_cached(self, image_item):
        if not hasattr(self.app_ref, 'ocr_cache'):
            return None

        try:
            if isinstance(image_item, Path):
                return self.app_ref.ocr_cache.get_for_path(image_item)
            pix = getattr(image_item, 'pixmap', None)
            if pix is not None:
                return self.app_ref.ocr_cache.get_for_pixmap(pix)
        except Exception:
            return None
        return None

    def load_image(self, image_item):
        if isinstance(image_item, Path):
            return self.imread_unicode(image_item)
        if hasattr(image_item, 'pixmap') and image_item.pixmap:
            return pixmap_to_cv(image_item.pixmap)
        return None

    def recognize_boxes(self, image_item, img_cv, boxes, frames, progress_callback=None):
        total = len(boxes)
        h_img, w_img = img_cv.shape[:2]

        for idx, box in enumerate(boxes):
            self.recognize_box(img_cv, box, w_img, h_img)

            if progress_callback is not None:
                progress_callback(idx + 1, total, self.token)

        self.save_cache(image_item, boxes, frames)

    def recognize_box(self, img_cv, box, w_img, h_img):
        x, y, w, h = box.rect.getRect()[0:4]
        x, y = max(0, x), max(0, y)
        w, h = min(w, w_img - x), min(h, h_img - y)
        if w <= 0 or h <= 0:
            return

        crop_img = img_cv[y:y+h, x:x+w]
        if crop_img is None or crop_img.size == 0:
            return

        try:
            pil_img = Image.fromarray(cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB))
        except Exception:
            return

        mocr_callable = getattr(self.app_ref, 'mocr', None)
        if callable(mocr_callable):
            try:
                box.text = mocr_callable(pil_img)
            except Exception:
                box.text = ""
        else:
            box.text = ""

    def save_cache(self, image_item, boxes, frames):
        if not hasattr(self.app_ref, 'ocr_cache'):
            return
        try:
            if isinstance(image_item, Path):
                self.app_ref.ocr_cache.set_for_path(image_item, boxes, frames)
            else:
                pix = getattr(image_item, 'pixmap', None)
                if pix is not None:
                    self.app_ref.ocr_cache.set_for_pixmap(pix, boxes, frames)
        except Exception:
            pass

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

            results = yolo_detector(image_cv, conf=0.25, iou=0.45, imgsz=640, classes=[2, 3])

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


class OCRThread(QThread):
    finished = Signal(list, list, object, object)
    progress = Signal(int, int, object)

    def __init__(self, app_ref, image_item, token=None):
        super().__init__()
        self.processor = OCRProcessor(app_ref, image_item, token)
        self.token = token

    def run(self):
        for boxes, frames, img_cv in self.processor.process(self.progress.emit):
            self.finished.emit(boxes, frames, img_cv, self.token)


class BatchThread(QThread):
    item_started = Signal(int, object)
    item_finished = Signal(int, object)
    stage_changed = Signal(str, int)
    stage_progress = Signal(int, int, str)
    all_done = Signal()

    def __init__(self, app_ref, entries, parent=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.entries = entries

    def run(self):
        prepared = []
        total_pages = len(self.entries)
        total_boxes = 0

        self.stage_changed.emit("Подготовка...", 0)
        for idx, path in enumerate(self.entries):
            processor = OCRProcessor(self.app_ref, path)
            cached = processor.get_cached(path)
            if cached:
                boxes, frames, _md5 = cached
                prepared.append((idx, path, boxes, frames, None, True))
            else:
                img_cv = processor.load_image(path)
                if img_cv is None:
                    boxes, frames = [], []
                else:
                    boxes, frames = processor.detect_text_boxes(img_cv)
                    total_boxes += len(boxes)
                prepared.append((idx, path, boxes, frames, img_cv, False))
            self.stage_progress.emit(
                idx + 1,
                total_pages,
                f"Подготовка: {idx + 1}/{total_pages} страниц",
            )

        self.stage_changed.emit("Распознавание...", total_boxes)
        recognized_boxes = 0
        processed_pages = 0
        for idx, path, boxes, frames, img_cv, cached in prepared:
            self.item_started.emit(idx, path)
            if not cached and img_cv is not None:
                processor = OCRProcessor(self.app_ref, path)
                h_img, w_img = img_cv.shape[:2]
                for box in boxes:
                    processor.recognize_box(img_cv, box, w_img, h_img)
                    recognized_boxes += 1
                    self.stage_progress.emit(
                        recognized_boxes,
                        total_boxes,
                        f"Страницы: {processed_pages}/{total_pages} | OCR: {recognized_boxes}/{total_boxes}",
                    )
                processor.save_cache(path, boxes, frames)
            processed_pages += 1
            self.stage_progress.emit(
                recognized_boxes if total_boxes else processed_pages,
                total_boxes if total_boxes else total_pages,
                f"Страницы: {processed_pages}/{total_pages} | OCR: {recognized_boxes}/{total_boxes}",
            )
            self.item_finished.emit(idx, (boxes, frames))

        self.all_done.emit()

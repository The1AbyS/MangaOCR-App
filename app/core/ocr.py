from PyQt5.QtCore import QThread, pyqtSignal, QRect
from .utils import MangaTextBox, pixmap_to_cv
from .cache import pixmap_md5
import cv2
import time
from PIL import Image

class OCRThread(QThread):
    finished = pyqtSignal(list, object, object)
    progress = pyqtSignal(int, int, object)

    def __init__(self, app_ref, image_item, token=None):
        super().__init__()
        self.app_ref = app_ref
        self.image_item = image_item
        self.token = token

    def run(self):
        start_time = time.time()

        if self.image_item.path:
            img_cv = self.app_ref.imread_unicode(self.image_item.path)
        elif self.image_item.pixmap:
            img_cv = pixmap_to_cv(self.image_item.pixmap)
        else:
            self.finished.emit([], None, getattr(self, 'token', None))
            print("OCR: пустое изображение, обработка заняла {:.3f} сек".format(time.time() - start_time))
            return

        boxes = self.app_ref.detect_text_boxes(img_cv)
        total = len(boxes)
        text_boxes = []
        h_img, w_img = img_cv.shape[:2]

        for idx, box in enumerate(boxes):
            x, y, w, h = cv2.boundingRect(box)
            x = max(0, x)
            y = max(0, y)
            w = min(w, w_img - x)
            h = min(h, h_img - y)
            self.progress.emit(idx + 1, total, getattr(self, 'token', None))
            if w <= 0 or h <= 0:
                continue
            crop_img = img_cv[y:y+h, x:x+w]
            if crop_img is None or crop_img.size == 0:
                continue
            try:
                pil_img = Image.fromarray(cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB))
            except Exception:
                continue
            text = self.app_ref.mocr(pil_img) if self.app_ref.mocr else ""
            rect = QRect(x, y, w, h)
            text_boxes.append(MangaTextBox(rect, text))
            self.progress.emit(idx + 1, total, getattr(self, 'token', None))

        self.finished.emit(text_boxes, img_cv, getattr(self, 'token', None))
        end_time = time.time()
        print(f"OCR: изображение обработано за {end_time - start_time:.3f} сек")

class BatchOCRThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)

    def __init__(self, app_ref, image_list):
        super().__init__()
        self.app_ref = app_ref
        self.image_list = image_list

    def run(self):
        results = []
        total = len(self.image_list)
        cache = self.app_ref.ocr_cache
        for idx, image_item in enumerate(self.image_list):
            if image_item.path:
                cache_key = image_item.path
            elif image_item.pixmap:
                cache_key = pixmap_md5(image_item.pixmap)
            else:
                continue

            if cache_key in cache:
                text_boxes, img_cv = cache[cache_key]
            else:
                if image_item.path:
                    img_cv = self.app_ref.imread_unicode(image_item.path)
                elif image_item.pixmap:
                    img_cv = pixmap_to_cv(self.image_item.pixmap)
                else:
                    continue

                boxes = self.app_ref.detect_text_boxes(img_cv)
                text_boxes = self.app_ref.group_and_recognize_lines(img_cv, boxes)
                cache[cache_key] = (text_boxes, img_cv)

            results.append((image_item, text_boxes))
            self.progress.emit(idx + 1, total)
        self.finished.emit(results)
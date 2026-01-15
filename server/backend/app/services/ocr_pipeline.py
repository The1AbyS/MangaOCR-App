from pathlib import Path
import cv2
import numpy as np
import hashlib
from PIL import Image
from typing import List, Callable, Optional, Union
from typing import List, Tuple

from app.core.state import app_state
#from app.services.utils import MangaTextBox
from app.schemas.ocr import MangaTextBox

def load_image(source: Union[str, Path, bytes, np.ndarray]) -> np.ndarray:
    if isinstance(source, Path) or isinstance(source, str):
        with open(source, "rb") as f:
            data = f.read()
        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

    if isinstance(source, bytes):
        return cv2.imdecode(np.frombuffer(source, np.uint8), cv2.IMREAD_COLOR)

    if isinstance(source, np.ndarray):
        return source

    raise TypeError("Unsupported image source")

def image_md5(image: np.ndarray) -> str:
    return hashlib.md5(image.tobytes()).hexdigest()

def detect_text_boxes(image_cv: np.ndarray) -> Tuple[List[MangaTextBox], List[MangaTextBox]]:
    boxes: List[MangaTextBox] = []
    frames: List[MangaTextBox] = []

    yolo = app_state.yolo
    if yolo is None:
        return boxes, frames

    results = yolo(image_cv, conf=0.25, iou=0.45)

    for r in results[0].boxes:
        cls = int(r.cls[0])
        x1, y1, x2, y2 = map(int, r.xyxy[0].cpu().numpy())

        box = MangaTextBox(
            x=x1,
            y=y1,
            w=x2 - x1,
            h=y2 - y1,
            text=""
        )

        if cls == 3:
            boxes.append(box)
        elif cls == 2:
            frames.append(box)

    return boxes, frames

def run_ocr_single(
    source,
    provided_boxes: Optional[List[MangaTextBox]] = None,
    progress_cb: Optional[Callable[[int, int], None]] = None,
    use_cache: bool = True,
):
    cache = getattr(app_state, "ocr_cache", None)

    # cache by path
    if use_cache and cache and isinstance(source, (str, Path)):
        cached = cache.get_for_path(source)
        if cached:
            return cached

    image = load_image(source)
    md5 = image_md5(image)

    # cache by md5
    if use_cache and cache:
        cached = cache.get_for_md5(md5)
        if cached:
            return cached

    if provided_boxes:
        boxes = provided_boxes
        frames = []
    else:
        boxes, frames = detect_text_boxes(image)

    h_img, w_img = image.shape[:2]

    for idx, box in enumerate(boxes):
        x, y, w, h = box.x, box.y, box.w, box.h
        x, y = max(0, x), max(0, y)
        w, h = min(w, w_img - x), min(h, h_img - y)

        if w <= 0 or h <= 0:
            continue

        crop = image[y:y + h, x:x + w]
        if crop.size == 0:
            continue

        try:
            pil_img = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
            box.text = app_state.mocr(pil_img)
        except Exception:
            box.text = ""

        if progress_cb:
            progress_cb(idx + 1, len(boxes))

    if cache:
        cache.set_for_md5(md5, boxes, frames)

    return boxes, frames, md5

def run_ocr_batch(
    sources: List[Union[str, Path, bytes]],
    progress_cb: Optional[Callable[[int, int], None]] = None,
):
    results = []

    for idx, source in enumerate(sources):
        if progress_cb:
            progress_cb(idx, len(sources))

        result = run_ocr_single(source)
        results.append(result)

    return results


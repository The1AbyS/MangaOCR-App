import re
import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
from pathlib import Path



# ---------------------------
# Вспомогательные функции
# ---------------------------

def natural_key(string: str):
    """Ключ для сортировки строк с числами естественным образом."""
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', string)]

def imread_unicode(path: Path) -> np.ndarray:
    """Читает изображение по пути, поддерживая Unicode."""
    with open(path, 'rb') as f:
        data = f.read()
    img_array = np.frombuffer(data, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img

# ---------------------------
# Модели данных
# ---------------------------

@dataclass
class MangaTextBox:
    x: int
    y: int
    w: int
    h: int
    text: str = ""

@dataclass
class ImageItem:
    """Объект изображения для OCR."""
    path: Optional[Path] = None
    boxes: List[MangaTextBox] = field(default_factory=list)

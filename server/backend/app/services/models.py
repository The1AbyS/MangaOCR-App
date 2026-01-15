import logging
from pathlib import Path
import numpy as np
from PIL import Image

from manga_ocr import MangaOcr
from ultralytics import YOLO

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


def load_models():
    """
    Загружает MangaOCR и YOLO модели из папки app/models.
    Прогоняет их на dummy-данных для прогрева.
    Возвращает: (mocr, yolo)
    """
    try:
        # --- Пути к моделям ---
        base_model_path = Path(__file__).parent.parent / "models"
        mocr_path = base_model_path / "model_manga_ocr"
        yolo_path = base_model_path / "yolo_m.pt"

        logger.info(f"Загрузка MangaOCR модели из: {mocr_path}")
        mocr = MangaOcr(pretrained_model_name_or_path=str(mocr_path))

        logger.info(f"Загрузка YOLO модели из: {yolo_path}")
        yolo = YOLO(str(yolo_path))

        # --- dummy прогон YOLO ---
        try:
            dummy_img = np.zeros((64, 64, 3), dtype=np.uint8)
            _ = yolo(dummy_img)
            logger.info("YOLO прогрев завершён")
        except Exception as e:
            logger.warning(f"Ошибка при прогреве YOLO: {e}")

        # --- dummy прогон MangaOCR ---
        try:
            dummy_pil = Image.new("RGB", (16, 16))
            try:
                _ = mocr(dummy_pil)
                logger.info("MangaOCR прогрев завершён")
            except Exception as e:
                logger.warning(f"Ошибка при прогреве MangaOCR: {e}")
        except Exception as e:
            logger.warning(f"Ошибка при создании dummy изображения для MangaOCR: {e}")

        logger.info("Модели успешно загружены")
        return mocr, yolo

    except Exception as e:
        logger.error(f"Ошибка при загрузке моделей: {e}", exc_info=True)
        raise RuntimeError(f"Не удалось загрузить модели: {e}") from e

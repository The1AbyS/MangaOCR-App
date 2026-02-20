import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QPixmap

class ImageParser(QThread):
    progress = Signal(str)         
    finished = Signal(list, Path)  

    def __init__(self, url: str, min_size=(400, 400), headers=None, timeout=10):
        super().__init__()
        self.url = url.strip()
        self.min_width, self.min_height = min_size
        self.session = requests.Session()
        self.session.headers.update(headers or {"User-Agent": "Mozilla/5.0"})
        self.timeout = timeout

    def run(self):
        try:
            self.progress.emit("Загрузка изображений...")
            image_urls = self.extract_image_urls(self.url)
            filtered_urls = self.filter_images(image_urls)

            if not filtered_urls:
                self.progress.emit("Не найдено изображений на странице.")
                self.finished.emit([], None)
                return

            out_dir = self.get_safe_folder(self.url)
            saved_files = self.download_images(filtered_urls, out_dir)

            self.progress.emit(f"Загружено {len(saved_files)} изображений в {out_dir}")
            self.finished.emit(saved_files, out_dir)

        except Exception as e:
            self.progress.emit(f"Ошибка при загрузке изображений: {e}")
            self.finished.emit([], None)

    def get_soup(self, url: str):
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "html.parser")

    def extract_image_urls(self, url: str):
        soup = self.get_soup(url)
        images = []
        for img in soup.find_all("img"):
            src = img.get("src")
            if not src:
                continue
            full_url = urljoin(url, src)
            images.append(full_url)
        return images

    def filter_images(self, urls):
        filtered = []
        for img_url in urls:
            try:
                resp = self.session.get(img_url, timeout=self.timeout)
                resp.raise_for_status()
                img = QPixmap()
                img.loadFromData(resp.content)
                if img.width() >= self.min_width and img.height() >= self.min_height:
                    filtered.append(img_url)
            except Exception:
                continue
        return filtered

    def get_safe_folder(self, url):
        safe_name = re.sub(r"[<>:\"/\\|?*]", "_", url.replace("http://", "").replace("https://", ""))
        out_dir = Path("MangaOCR_downloads", safe_name)
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def download_images(self, image_urls, out_dir: Path):
        saved = []
        total = len(image_urls)
        for i, url in enumerate(image_urls, start=1):
            try:
                r = self.session.get(url, timeout=self.timeout)
                r.raise_for_status()
                ext = url.split("?")[0].split(".")[-1]
                filename = out_dir / f"{i:03}.{ext}"
                with open(filename, "wb") as f:
                    f.write(r.content)
                saved.append(filename)

                self.progress.emit(f"Скачано {i} из {total} изображений...")

            except Exception as e:
                self.progress.emit(f"Ошибка при скачивании {url}: {e}")
                continue
        return saved
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
from PySide6.QtCore import QThread

class ImageParser(QThread):
    def __init__(self, headers=None, timeout=10):
        super().__init__()
        self.session = requests.Session()
        self.session.headers.update(headers or {
            "User-Agent": "Mozilla/5.0"
        })
        self.timeout = timeout

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

    def download_images(self, image_urls, out_dir: str):
        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        saved = []
        for i, url in enumerate(image_urls, start=1):
            r = self.session.get(url, timeout=self.timeout)
            r.raise_for_status()

            ext = url.split("?")[0].split(".")[-1]
            filename = out_path / f"{i:03}.{ext}"

            with open(filename, "wb") as f:
                f.write(r.content)

            saved.append(filename)

        return saved

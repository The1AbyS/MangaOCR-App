import json
from pathlib import Path

class CacheFolder:
    def __init__(self, cache_file=None, max_items=10):
        self.max_items = max_items
        self.cache_file = cache_file or Path.home() / ".mangaocr_recent_folders.json"
        self.folders = []
        self._load_cache()

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.folders = [Path(p) for p in data]
            except:
                self.folders = []

    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump([str(p) for p in self.folders], f)
        except:
            pass

    def add(self, path: Path):
        path = Path(path)
        self.folders = [p for p in self.folders if p != path]
        self.folders.insert(0, path)
        if len(self.folders) > self.max_items:
            self.folders = self.folders[:self.max_items]
        self._save_cache()

    def get_all(self):
        return self.folders

    def clear(self):
        self.folders = []
        self._save_cache()

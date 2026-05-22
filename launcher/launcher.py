import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QDialog,
    QDialogButtonBox,
    QProgressBar,
    QRadioButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


REPO_OWNER = "The1AbyS"
REPO_NAME = "MangaOCR-App"
BRANCH = "main"
APP_USER_MODEL_ID = "The1AbyS.MangaOCRApp.Launcher"
REPO_ZIP_URL = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/archive/refs/heads/{BRANCH}.zip"
COMMIT_API_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits/{BRANCH}"
WINDOWLESS_PROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
PYTHON_ZIP_URL = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
DRIVE_FILE_URL = "https://drive.google.com/uc?id=1mEM5KFc-I1HAA3YkK9gapvxYcphaCzXG"
DRIVE_OCR_URL = "https://drive.google.com/drive/folders/1m9sQIvEGom-2BP4iwqdF8wiFCyfLfi03"

LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home()))
DEFAULT_INSTALL_ROOT = LOCALAPPDATA / "MangaOCR-App"
CONFIG_DIR = LOCALAPPDATA / "MangaOCR"
CONFIG_FILE = CONFIG_DIR / "config.json"
LEGACY_CONFIG_FILE = LOCALAPPDATA / "MangaOCR-Launcher" / "config.json"
VERSION_FILE = ".launcher-version.json"
CRASH_LOG = "launcher-crash.log"

ICON_RELATIVE_PATH = Path("app", "ui", "icons", "Mocr.ico")
BUNDLED_APP_ZIP = Path("launcher_payload", "app_source.zip")
BUNDLED_MANIFEST = Path("launcher_payload", "manifest.json")

MODEL_DOWNLOAD_ATTEMPTS = 3
OCR_REQUIRED_FILES = {
    "config.json",
    "preprocessor_config.json",
    "pytorch_model.bin",
    "tokenizer_config.json",
}
CYRILLIC_CHARS = set("АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя")

BASE_PACKAGES = [
    "PySide6",
    "opencv-python",
    "numpy",
    "pillow",
    "manga-ocr",
    "loguru",
    "scikit-image",
    "ultralytics",
    "python-docx",
    "requests",
    "beautifulsoup4",
    "gdown",
    "qt_material_icons",
]
TORCH_CPU = ["torch", "torchvision", "torchaudio"]
TORCH_GPU = [
    "torch==2.7.1",
    "torchvision==0.22.1",
    "torchaudio==2.7.1",
    "--index-url",
    "https://download.pytorch.org/whl/cu118",
]
PIP_NETWORK_OPTIONS = ["--timeout", "120", "--retries", "5"]


class InstallPaths:
    def __init__(self, install_root):
        self.root = Path(install_root).expanduser().resolve()
        self.app_dir = self.root / "source"
        self.python_dir = self.root / "python"
        self.python_exe = self.python_dir / "python.exe"
        self.pythonw_exe = self.python_dir / "pythonw.exe"
        self.req_file = self.app_dir / "requirements" / "requirements.txt"
        self.model_dir = self.app_dir / "models"
        self.model_file = self.model_dir / "yolo_m.pt"
        self.model_ocr = self.model_dir / "model_manga_ocr"
        self.run_file = self.app_dir / "run.pyw"
        self.version_file = self.root / VERSION_FILE
        self.crash_log = self.root / CRASH_LOG

    def is_installed(self):
        return self.run_file.exists() and self.pythonw_exe.exists()

    def models_ready(self):
        if not self.model_file.exists() or not self.model_ocr.exists():
            return False
        existing_files = {path.name for path in self.model_ocr.iterdir() if path.is_file()}
        return OCR_REQUIRED_FILES.issubset(existing_files)


def load_config():
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    try:
        return json.loads(LEGACY_CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_config(config):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def configured_install_root():
    config = load_config()
    return Path(config.get("install_root") or DEFAULT_INSTALL_ROOT)


def bundled_path(relative_path):
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    if not getattr(sys, "frozen", False) and relative_path.parts[:1] == ("launcher_payload",):
        return base_path / "launcher" / "build_assets" / relative_path.name
    return base_path / relative_path


def set_windows_app_user_model_id(app_id=APP_USER_MODEL_ID):
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def has_cyrillic(text):
    return any(char in CYRILLIC_CHARS for char in text)


def validate_install_root(path_text):
    if not path_text.strip():
        return "Выберите папку установки."
    try:
        path = Path(path_text).expanduser().resolve()
    except OSError as exc:
        return f"Некорректный путь установки: {exc}"

    anchor = Path(path.anchor) if path.anchor else None
    if anchor and path == anchor:
        return "Нельзя устанавливать приложение прямо в корень диска. Выберите отдельную папку."
    if has_cyrillic(str(path)):
        return "В пути установки не должно быть кириллицы. Выберите папку с латиницей, например C:\\Apps\\MangaOCR-App."
    return None


def read_bundled_manifest():
    manifest_path = bundled_path(BUNDLED_MANIFEST)
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


class LauncherWorker(QThread):
    log_signal = Signal(str)
    progress_signal = Signal(int)
    status_signal = Signal(str)
    finished_signal = Signal(bool)

    def __init__(self, action, install_root, torch_variant="cpu"):
        super().__init__()
        self.action = action
        self.torch_variant = torch_variant
        self.paths = InstallPaths(install_root)
        self.remote_sha = None

    def log(self, text):
        self.log_signal.emit(text)

    def set_progress(self, value, text):
        self.progress_signal.emit(value)
        self.status_signal.emit(text)
        self.log(text)

    def request_json(self, url):
        request = urllib.request.Request(url, headers={"User-Agent": "MangaOCR-Launcher"})
        with urllib.request.urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    def run_process(self, args, cwd=None):
        shown = " ".join(str(part) for part in args)
        self.log(f"> {shown}")
        process = subprocess.Popen(
            [str(part) for part in args],
            cwd=str(cwd or self.paths.app_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=WINDOWLESS_PROCESS_FLAGS,
        )
        assert process.stdout is not None
        for line in process.stdout:
            self.log(line.rstrip())
        code = process.wait()
        if code:
            raise RuntimeError(f"Команда завершилась с кодом {code}: {shown}")

    def run_process_with_retries(self, args, cwd=None, attempts=MODEL_DOWNLOAD_ATTEMPTS):
        last_error = None
        for attempt in range(1, attempts + 1):
            try:
                self.run_process(args, cwd=cwd)
                return
            except RuntimeError as exc:
                last_error = exc
                if attempt == attempts:
                    break
                self.log(f"Скачивание оборвалось. Повтор {attempt + 1}/{attempts}...")
        raise last_error

    def run(self):
        try:
            validation_error = validate_install_root(str(self.paths.root))
            if validation_error:
                raise RuntimeError(validation_error)

            if self.action == "setup":
                self.setup_all(force_update=True)
            elif self.action == "auto":
                self.auto_update_and_run()
            elif self.action == "update":
                self.set_progress(10, "Обновляю файлы приложения...")
                self.update_app_if_needed(force=True)
                self.set_progress(100, "Файлы приложения обновлены.")
            elif self.action == "install":
                self.set_progress(10, "Проверяю локальный Python...")
                self.ensure_python()
                self.set_progress(40, "Устанавливаю зависимости...")
                self.install_dependencies()
                self.set_progress(100, "Зависимости установлены.")
            elif self.action == "models":
                self.set_progress(10, "Проверяю локальный Python...")
                self.ensure_python()
                self.set_progress(55, "Скачиваю модели...")
                self.download_models()
                self.set_progress(100, "Модели готовы.")
            elif self.action == "run_app":
                self.set_progress(100, "Запускаю приложение...")
                self.launch_app()

            self.finished_signal.emit(True)
        except Exception as exc:
            self.log(f"Ошибка: {exc}")
            self.finished_signal.emit(False)

    def setup_all(self, force_update=False):
        self.set_progress(5, "Проверяю файлы приложения...")
        self.update_app_if_needed(force=force_update)
        self.set_progress(25, "Проверяю локальный Python...")
        self.ensure_python()
        self.set_progress(45, "Устанавливаю зависимости...")
        self.install_dependencies()
        self.set_progress(80, "Проверяю модели...")
        self.download_models()
        self.set_progress(100, "Запускаю приложение...")
        self.launch_app()

    def auto_update_and_run(self):
        if not self.paths.is_installed():
            self.log("Установка не завершена. Запускаю полную установку.")
            self.setup_all(force_update=True)
            return

        self.set_progress(10, "Проверяю обновления...")
        updated = self.update_app_if_needed(force=False)
        if updated:
            self.set_progress(55, "После обновления проверяю зависимости...")
            self.install_dependencies()

        if not self.paths.models_ready():
            self.set_progress(80, "Докачиваю недостающие модели...")
            self.download_models()

        self.set_progress(100, "Запускаю приложение...")
        self.launch_app()

    def installed_version(self):
        try:
            return json.loads(self.paths.version_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def save_installed_version(self, data):
        self.paths.root.mkdir(parents=True, exist_ok=True)
        self.paths.version_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def update_app_if_needed(self, force=False):
        self.paths.root.mkdir(parents=True, exist_ok=True)
        self.log(f"Папка установки: {self.paths.root}")

        installed = self.installed_version()
        bundled_zip = bundled_path(BUNDLED_APP_ZIP)
        bundled_manifest = read_bundled_manifest()
        bundled_revision = bundled_manifest.get("git") if bundled_manifest else None
        installed_revision = installed.get("sha") or installed.get("git")

        self.remote_sha = self.latest_remote_sha()
        if self.remote_sha:
            if not force and self.paths.run_file.exists() and installed_revision == self.remote_sha:
                self.log("Обновлений нет.")
                return False

            if bundled_zip.exists() and bundled_manifest and bundled_revision == self.remote_sha:
                if not force and self.paths.run_file.exists() and installed.get("bundle_id") == bundled_manifest.get("bundle_id"):
                    self.log("Установлена актуальная bundled-версия.")
                    return False
                self.install_from_zip(bundled_zip)
                self.save_installed_version({"source": "bundled", "sha": self.remote_sha, **bundled_manifest})
                self.log("Файлы приложения установлены из встроенного архива.")
                return True

            try:
                return self.update_from_github(force=force, remote_sha=self.remote_sha)
            except (OSError, urllib.error.URLError, TimeoutError) as exc:
                self.log(f"Не удалось скачать обновление с GitHub: {exc}")
                if not bundled_zip.exists() or not bundled_manifest:
                    raise
                if not force and self.paths.run_file.exists():
                    self.log("Запускаю установленную версию.")
                    return False
                self.install_from_zip(bundled_zip)
                self.save_installed_version({"source": "bundled", **bundled_manifest})
                self.log("Файлы приложения установлены из встроенного архива.")
                return True

        if bundled_zip.exists() and bundled_manifest:
            if not force and self.paths.run_file.exists() and installed.get("bundle_id") == bundled_manifest.get("bundle_id"):
                self.log("Установлена актуальная bundled-версия.")
                return False
            self.install_from_zip(bundled_zip)
            self.save_installed_version({"source": "bundled", **bundled_manifest})
            self.log("Файлы приложения установлены из встроенного архива.")
            return True

        return self.update_from_github(force=force)

    def update_from_github(self, force=False, remote_sha=None):
        self.remote_sha = remote_sha if remote_sha is not None else self.latest_remote_sha()
        installed = self.installed_version()
        installed_revision = installed.get("sha") or installed.get("git")

        if not force and self.paths.run_file.exists() and self.remote_sha and installed_revision == self.remote_sha:
            self.log("Обновлений нет.")
            return False
        if not force and self.paths.run_file.exists() and self.remote_sha is None:
            self.log("Проверка обновлений не удалась, запускаю установленную версию.")
            return False

        with tempfile.TemporaryDirectory(prefix="mangaocr-launcher-") as tmp:
            zip_path = Path(tmp) / "app.zip"
            self.log("Скачиваю приложение с GitHub...")
            urllib.request.urlretrieve(REPO_ZIP_URL, zip_path)
            self.install_from_zip(zip_path)

        self.save_installed_version({"source": "github", "sha": self.remote_sha})
        self.log("Файлы приложения готовы.")
        return True

    def latest_remote_sha(self):
        try:
            data = self.request_json(COMMIT_API_URL)
            return data.get("sha")
        except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            self.log(f"Не удалось проверить обновления: {exc}")
            return None

    def install_from_zip(self, zip_path):
        with tempfile.TemporaryDirectory(prefix="mangaocr-extract-") as tmp:
            extract_dir = Path(tmp) / "extract"
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(extract_dir)
            roots = [path for path in extract_dir.iterdir() if path.is_dir()]
            source = roots[0] if len(roots) == 1 and not (extract_dir / "run.pyw").exists() else extract_dir
            self.paths.app_dir.mkdir(parents=True, exist_ok=True)
            self.copy_tree(source, self.paths.app_dir)

    def copy_tree(self, source, destination):
        ignored_dirs = {".git", ".ruff_cache", "__pycache__", "launcher", "MangaOCR_downloads"}
        ignored_files = {".gitattributes"}
        for item in source.iterdir():
            if item.name in ignored_dirs or item.name in ignored_files:
                continue
            target = destination / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)

    def ensure_python(self):
        if self.paths.python_exe.exists():
            self.log(f"Локальный Python уже установлен: {self.paths.python_dir}")
            return
        self.paths.python_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="mangaocr-python-") as tmp:
            tmp_path = Path(tmp)
            python_zip = tmp_path / "python.zip"
            get_pip = tmp_path / "get-pip.py"
            self.log("Скачиваю embedded Python 3.11...")
            urllib.request.urlretrieve(PYTHON_ZIP_URL, python_zip)
            with zipfile.ZipFile(python_zip) as archive:
                archive.extractall(self.paths.python_dir)
            self.enable_embedded_python_site_packages()
            self.log("Устанавливаю pip в локальный Python...")
            urllib.request.urlretrieve(GET_PIP_URL, get_pip)
            self.run_process([self.paths.python_exe, get_pip, "--no-warn-script-location"], cwd=self.paths.root)
        self.log("Локальный Python готов.")

    def enable_embedded_python_site_packages(self):
        for pth_file in self.paths.python_dir.glob("python*._pth"):
            text = pth_file.read_text(encoding="utf-8")
            pth_file.write_text(text.replace("#import site", "import site"), encoding="utf-8")
            return
        raise RuntimeError("Не найден ._pth файл embedded Python.")

    def install_dependencies(self):
        if not self.paths.req_file.exists():
            raise RuntimeError("requirements.txt не найден. Сначала обновите приложение.")

        self.log("Обновляю pip...")
        self.run_process(
            [self.paths.python_exe, "-m", "pip", "install", *PIP_NETWORK_OPTIONS, "--upgrade", "pip"],
            cwd=self.paths.root,
        )

        packages = self.read_requirements()
        if "gdown" not in packages:
            packages.append("gdown")
        self.log("Устанавливаю зависимости приложения...")
        self.run_process(
            [self.paths.python_exe, "-m", "pip", "install", *PIP_NETWORK_OPTIONS, "--no-warn-script-location", *packages],
            cwd=self.paths.root,
        )

        self.log(f"Устанавливаю PyTorch: {self.torch_variant.upper()}")
        torch_packages = TORCH_GPU if self.torch_variant == "gpu" else TORCH_CPU
        self.run_process(
            [self.paths.python_exe, "-m", "pip", "install", *PIP_NETWORK_OPTIONS, "--no-warn-script-location", *torch_packages],
            cwd=self.paths.root,
        )
        self.log("Зависимости готовы.")

    def read_requirements(self):
        packages = []
        for raw_line in self.paths.req_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line == "PyQtWebEngine":
                continue
            packages.append(line)
        return packages or BASE_PACKAGES

    def download_models(self):
        self.paths.model_dir.mkdir(parents=True, exist_ok=True)
        if not self.paths.model_file.exists():
            self.log("Скачиваю yolo_m.pt...")
            self.run_process_with_retries(
                [self.paths.python_exe, "-m", "gdown", DRIVE_FILE_URL, "-O", self.paths.model_file],
                cwd=self.paths.app_dir,
            )
        else:
            self.log("OK: yolo_m.pt уже есть.")

        if not self.paths.models_ready():
            self.log("Скачиваю model_manga_ocr...")
            self.paths.model_ocr.mkdir(parents=True, exist_ok=True)
            self.run_process_with_retries(
                [self.paths.python_exe, "-m", "gdown", DRIVE_OCR_URL, "--folder", "-O", self.paths.model_ocr],
                cwd=self.paths.app_dir,
            )
            if not self.paths.models_ready():
                raise RuntimeError("model_manga_ocr скачалась не полностью. Нажмите 'Скачать модели' ещё раз.")
        else:
            self.log("OK: model_manga_ocr уже есть.")

    def launch_app(self):
        if not self.paths.run_file.exists():
            raise RuntimeError("run.pyw не найден. Сначала установите или обновите приложение.")
        if not self.paths.pythonw_exe.exists():
            raise RuntimeError("pythonw.exe не найден. Сначала установите зависимости.")

        self.log("Запускаю MangaOCR App...")
        bootstrap = (
            "import os, runpy, sys, traceback\n"
            "if sys.platform == 'win32':\n"
            "    try:\n"
            "        import ctypes\n"
            "        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('The1AbyS.MangaOCRApp.App')\n"
            "    except Exception:\n"
            "        pass\n"
            f"app_dir = {str(self.paths.app_dir)!r}\n"
            f"run_file = {str(self.paths.run_file)!r}\n"
            f"crash_log = {str(self.paths.crash_log)!r}\n"
            "os.environ['MANGAOCR_APP_DIR'] = app_dir\n"
            "try:\n"
            "    os.chdir(app_dir)\n"
            "    sys.path.insert(0, app_dir)\n"
            "    runpy.run_path(run_file, run_name='__main__')\n"
            "except Exception:\n"
            "    with open(crash_log, 'w', encoding='utf-8') as handle:\n"
            "        traceback.print_exc(file=handle)\n"
            "    raise\n"
        )
        subprocess.Popen(
            [str(self.paths.pythonw_exe), "-c", bootstrap],
            cwd=str(self.paths.app_dir),
            creationflags=WINDOWLESS_PROCESS_FLAGS,
        )
        self.log(f"Если окно не открылось, проверьте лог: {self.paths.crash_log}")


class SplashWindow(QWidget):
    def __init__(self, icon_path=None):
        super().__init__()
        self.setWindowTitle("MangaOCR")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(520, 360)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(16, 16, 16, 16)

        panel = QFrame()
        panel.setObjectName("SplashPanel")
        shadow = QGraphicsDropShadowEffect(panel)
        shadow.setBlurRadius(22)
        shadow.setOffset(0, 8)
        shadow.setColor(Qt.GlobalColor.black)
        panel.setGraphicsEffect(shadow)
        outer_layout.addWidget(panel)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(34, 24, 34, 24)
        layout.setSpacing(10)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if icon_path and Path(icon_path).exists():
            pixmap = QIcon(str(icon_path)).pixmap(68, 68)
            self.icon_label.setPixmap(
                pixmap.scaled(68, 68, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )
        layout.addWidget(self.icon_label)

        title = QLabel("MangaOCR")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #ffffff;")
        layout.addWidget(title)

        subtitle = QLabel("Подготовка рабочего окружения")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 12px; color: #b8b8b8;")
        layout.addWidget(subtitle)

        self.status_label = QLabel("Запуск...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #e6e6e6;")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet(
            """
            QProgressBar {
                min-height: 8px;
                border: 1px solid #3a3a3a;
                border-radius: 4px;
                background: #181818;
            }
            QProgressBar::chunk {
                border-radius: 3px;
                background: #686868;
            }
            """
        )
        layout.addWidget(self.progress)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFixedHeight(88)
        self.log_view.setStyleSheet(
            """
            QTextEdit {
                border: 1px solid #393939;
                border-radius: 4px;
                background: #1d1d1d;
                color: #bdbdbd;
                font-size: 11px;
            }
            """
        )
        layout.addWidget(self.log_view)

        self.setStyleSheet(
            """
            #SplashPanel {
                background: #252525;
                border: 1px solid #3f3f3f;
                border-radius: 8px;
            }
            """
        )

    def set_status(self, text):
        self.status_label.setText(text)

    def set_progress(self, value):
        self.progress.setValue(value)

    def append_log(self, text):
        self.log_view.append(text)


class FirstRunDialog(QDialog):
    def __init__(self, install_path, torch_variant="cpu", icon_path=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MangaOCR")
        if icon_path and Path(icon_path).exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setFixedWidth(560)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Первый запуск MangaOCR")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        note = QLabel("Выберите папку установки и вариант ускорения для моделей YOLO/manga-ocr. GPU быстрее, но требует NVIDIA и подходящий драйвер.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #b8b8b8;")
        layout.addWidget(note)

        install_row = QHBoxLayout()
        install_row.addWidget(QLabel("Папка установки:"))
        self.install_path = QLineEdit(str(install_path))
        install_row.addWidget(self.install_path, 1)
        browse_btn = QPushButton("Выбрать")
        browse_btn.clicked.connect(self.choose_folder)
        install_row.addWidget(browse_btn)
        layout.addLayout(install_row)

        self.cpu_radio = QRadioButton("CPU")
        self.cpu_radio.setToolTip("Самый совместимый вариант.")
        self.gpu_radio = QRadioButton("GPU NVIDIA / CUDA 11.8")
        self.gpu_radio.setToolTip("Ставит GPU-версию PyTorch.")
        if torch_variant == "gpu":
            self.gpu_radio.setChecked(True)
        else:
            self.cpu_radio.setChecked(True)
        layout.addWidget(self.cpu_radio)
        layout.addWidget(self.gpu_radio)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку установки MangaOCR", self.install_path.text())
        if folder:
            self.install_path.setText(folder)

    def torch_variant(self):
        return "gpu" if self.gpu_radio.isChecked() else "cpu"


class LauncherGUI(QWidget):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.buttons = []
        self.config = load_config()
        self.splash = None
        self.splash_started_at = 0
        self.splash_min_msec = 300
        self.auto_start = self.should_auto_start()

        self.setWindowTitle("MangaOCR")
        icon_path = bundled_path(ICON_RELATIVE_PATH)
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.setFixedSize(820, 600)

        layout = QVBoxLayout(self)

        install_row = QHBoxLayout()
        install_row.addWidget(QLabel("Папка установки:"))
        self.install_path = QLineEdit(str(configured_install_root()))
        install_row.addWidget(self.install_path, 1)
        browse_btn = QPushButton("Выбрать")
        browse_btn.clicked.connect(self.choose_install_folder)
        install_row.addWidget(browse_btn)
        self.buttons.append(browse_btn)
        layout.addLayout(install_row)

        torch_row = QHBoxLayout()
        torch_row.addWidget(QLabel("PyTorch:"))
        self.torch_combo = QComboBox()
        self.torch_combo.addItem("CPU", "cpu")
        self.torch_combo.addItem("GPU NVIDIA / CUDA 11.8", "gpu")
        saved_torch = self.config.get("torch_variant", "cpu")
        self.torch_combo.setCurrentIndex(1 if saved_torch == "gpu" else 0)
        torch_row.addWidget(self.torch_combo, 1)
        layout.addLayout(torch_row)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(self.log_view, 1)

        self.status_label = QLabel("Готов к запуску.")
        layout.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        self.progress.setTextVisible(True)
        self.progress.setStyleSheet(
            """
            QProgressBar {
                min-height: 22px;
                border: 1px solid #b8bec8;
                border-radius: 6px;
                background: #f3f5f8;
                text-align: center;
                color: #20242a;
            }
            QProgressBar::chunk {
                border-radius: 5px;
                background: #2f7dd1;
            }
            """
        )
        layout.addWidget(self.progress)

        self.add_button(layout, "Установить всё и запустить", "setup")
        self.add_button(layout, "Обновить файлы приложения", "update")
        self.add_button(layout, "Переустановить зависимости", "install")
        self.add_button(layout, "Скачать модели", "models")
        self.add_button(layout, "Запустить / проверить обновления", "auto")

    def start_auto_splash(self):
        icon_path = bundled_path(ICON_RELATIVE_PATH)
        self.splash = SplashWindow(icon_path if icon_path.exists() else None)
        self.splash_started_at = time.monotonic()
        self.splash.show()
        action = "auto" if InstallPaths(self.install_path.text()).is_installed() else "setup"
        QTimer.singleShot(100, lambda: self.start_worker(action))

    def should_auto_start(self):
        if "--no-auto-start" in sys.argv:
            return False
        return True

    def prepare_first_run(self):
        if InstallPaths(self.install_path.text()).is_installed():
            return True

        while True:
            icon_path = bundled_path(ICON_RELATIVE_PATH)
            dialog = FirstRunDialog(
                self.install_path.text(),
                self.torch_combo.currentData(),
                icon_path if icon_path.exists() else None,
                self,
            )
            if dialog.exec() != QDialog.Accepted:
                return False
            folder = dialog.install_path.text().strip()
            validation_error = validate_install_root(folder)
            if validation_error:
                QMessageBox.warning(self, "MangaOCR", validation_error)
                continue
            self.install_path.setText(folder)
            self.torch_combo.setCurrentIndex(1 if dialog.torch_variant() == "gpu" else 0)
            self.save_current_config()
            return True

    def choose_install_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку установки", self.install_path.text())
        if folder:
            validation_error = validate_install_root(folder)
            if validation_error:
                QMessageBox.warning(self, "MangaOCR", validation_error)
                return
            self.install_path.setText(folder)
            self.save_current_config()

    def save_current_config(self):
        save_config(
            {
                "install_root": self.install_path.text().strip() or str(DEFAULT_INSTALL_ROOT),
                "torch_variant": self.torch_combo.currentData(),
            }
        )

    def add_button(self, layout, text, action):
        button = QPushButton(text)
        button.clicked.connect(lambda: self.start_worker(action))
        layout.addWidget(button)
        self.buttons.append(button)
        return button

    def start_worker(self, action):
        if self.worker and self.worker.isRunning():
            return
        validation_error = validate_install_root(self.install_path.text())
        if validation_error:
            QMessageBox.warning(self, "MangaOCR", validation_error)
            return
        self.save_current_config()
        self.set_buttons_enabled(False)
        self.progress.setValue(0)
        self.worker = LauncherWorker(action, self.install_path.text(), self.torch_combo.currentData())
        self.worker.log_signal.connect(self.update_log)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.status_signal.connect(self.status_label.setText)
        if self.splash:
            self.worker.log_signal.connect(self.splash.append_log)
            self.worker.progress_signal.connect(self.splash.set_progress)
            self.worker.status_signal.connect(self.splash.set_status)
        self.worker.finished_signal.connect(lambda ok: self.worker_finished(ok, action))
        self.worker.start()

    def set_buttons_enabled(self, enabled):
        for button in self.buttons:
            button.setEnabled(enabled)
        self.torch_combo.setEnabled(enabled)
        self.install_path.setEnabled(enabled)

    def update_log(self, text):
        self.log_view.append(text)

    def worker_finished(self, ok, action):
        self.set_buttons_enabled(True)
        if ok:
            self.status_label.setText("Готово.")
            self.update_log("Готово.")
            if self.splash:
                self.finish_auto_start()
        else:
            if self.splash:
                self.splash.close()
                self.splash = None
                self.show()
            self.status_label.setText("Ошибка. Подробности в логе.")
            QMessageBox.warning(self, "MangaOCR", "Операция завершилась с ошибкой. Подробности в логе.")

    def finish_auto_start(self):
        if not self.splash:
            self.close()
            return
        elapsed_msec = int((time.monotonic() - self.splash_started_at) * 1000)
        delay_msec = max(0, self.splash_min_msec - elapsed_msec)
        self.splash.set_progress(100)
        self.splash.set_status("Готово")
        QTimer.singleShot(delay_msec, self.close_auto_start)

    def close_auto_start(self):
        if self.splash:
            self.splash.close()
            self.splash = None
        self.close()


if __name__ == "__main__":
    set_windows_app_user_model_id()
    app = QApplication(sys.argv)
    app_icon_path = bundled_path(ICON_RELATIVE_PATH)
    if app_icon_path.exists():
        app.setWindowIcon(QIcon(str(app_icon_path)))
    window = LauncherGUI()
    if window.auto_start:
        if window.prepare_first_run():
            window.start_auto_splash()
        else:
            window.close()
            sys.exit(0)
    else:
        window.show()
    sys.exit(app.exec())

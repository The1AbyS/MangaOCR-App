from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QGridLayout, QFrame, QFileDialog,
    QInputDialog, QMenu, QMessageBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QTimer, QSettings, QSize, QThread
from PySide6.QtGui import QPixmap, QDesktopServices, QCursor, QIcon
import os
import shutil
from pathlib import Path


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
IMAGE_EXTENSIONS_ALL = (".png", ".jpg", ".jpeg", ".webp", ".tiff")
PREVIEWS_DIR = Path.home() / ".mangaocr_previews"


def _preview_key(project_path: str) -> str:
    import hashlib
    return hashlib.md5(str(Path(project_path).resolve()).encode()).hexdigest()


def _custom_preview_path(project_path: str, ext: str = "") -> Path:
    return PREVIEWS_DIR / (_preview_key(project_path) + ext)


def find_custom_preview(project_path: str) -> str | None:
    if not PREVIEWS_DIR.exists():
        return None
    key = _preview_key(project_path)
    for ext in IMAGE_EXTENSIONS:
        candidate = PREVIEWS_DIR / (key + ext)
        if candidate.exists():
            return str(candidate)
    return None


def find_preview(folder: str) -> str | None:
    custom = find_custom_preview(folder)
    if custom:
        return custom

    try:
        for file in sorted(os.listdir(folder)):
            if file.lower().endswith(IMAGE_EXTENSIONS):
                return os.path.join(folder, file)
    except OSError:
        pass
    return None


def set_custom_preview(project_path: str, image_path: str) -> bool:
    ext = Path(image_path).suffix.lower()
    if ext not in IMAGE_EXTENSIONS:
        return False
    try:
        PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
        remove_custom_preview(project_path)
        dest = _custom_preview_path(project_path, ext)
        shutil.copy2(image_path, dest)
        return True
    except OSError:
        return False


def remove_custom_preview(project_path: str) -> bool:
    key = _preview_key(project_path)
    removed = False
    for ext in IMAGE_EXTENSIONS:
        candidate = PREVIEWS_DIR / (key + ext)
        try:
            candidate.unlink()
            removed = True
        except FileNotFoundError:
            pass
        except OSError:
            pass
    return removed


def count_images(folder: str) -> int:
    try:
        return sum(
            1 for f in os.listdir(folder)
            if f.lower().endswith(IMAGE_EXTENSIONS_ALL)
        )
    except OSError:
        return 0


def build_project_list(folder: str) -> list[dict]:
    projects = []
    try:
        for name in sorted(os.listdir(folder)):
            full_path = os.path.join(folder, name)

            if not os.path.isdir(full_path):
                continue

            try:
                items = os.listdir(full_path)
            except OSError:
                items = []

            image_count = sum(
                1 for f in items
                if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
            )

            folder_count = sum(
                1 for f in items
                if os.path.isdir(os.path.join(full_path, f))
            )

            projects.append({
                "name": name,
                "path": full_path,
                "preview": find_preview(full_path),
                "image_count": image_count,
                "folder_count": folder_count,
            })

    except OSError as e:
        raise RuntimeError(f"Не удалось прочитать папку: {e}") from e

    return projects


class PreviewLoaderThread(QThread):
    preview_ready = Signal(str, QPixmap)

    def __init__(self, paths: list[str], size: QSize, parent=None):
        super().__init__(parent)
        self.paths = paths
        self.size = size

    def run(self):
        for path in self.paths:
            if not path or not os.path.exists(path):
                continue
            pix = QPixmap(path).scaled(
                self.size, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.preview_ready.emit(path, pix)


class ProjectCard(QFrame):
    clicked = Signal(dict)
    rename_requested = Signal(dict)
    delete_requested = Signal(dict)
    open_folder_requested = Signal(str)
    set_preview_requested = Signal(dict)
    reset_preview_requested = Signal(dict)

    PREVIEW_SIZE = QSize(180, 155)

    def __init__(self, data: dict, parent=None):
        super().__init__(parent)
        self.data = data
        self.setObjectName("ProjectCard")
        self.setFixedSize(200, 235)
        self.setCursor(Qt.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        self.preview = QLabel()
        self.preview.setFixedSize(self.PREVIEW_SIZE)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet("background: #1e1e1e; border-radius: 8px;")
        self.preview.setText("...")

        self.title = QLabel(data.get("name", "Без названия"))
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-weight: 500; font-size: 13px;")

        count = data.get("image_count", 0)
        folders = data.get("folder_count", 0)
        parts = []
        if count:
            parts.append(f"{count} изображений")
        if folders:
            parts.append(f"{folders} папок")
        
        self.info = QLabel(" | ".join(parts))
        self.info.setAlignment(Qt.AlignCenter)
        self.info.setStyleSheet("color: #aaaaaa; font-size: 11px;")

        layout.addWidget(self.preview)
        layout.addWidget(self.title)
        layout.addWidget(self.info)

        self.setStyleSheet("""
        QFrame#ProjectCard {
            border: 1px solid #555;
            border-radius: 12px;
            background: #2b2b2b;
        }
        QFrame#ProjectCard:hover {
            border: 1px solid #888;
            background: #363636;
        }
        """)

    def set_preview_pixmap(self, pixmap: QPixmap):
        self.preview.setPixmap(pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.data)

    def contextMenuEvent(self, event):
        if self.data.get("is_button"):
            return
        menu = QMenu(self)
        menu.addAction("Переименовать", lambda: self.rename_requested.emit(self.data))
        menu.addAction("Удалить проект", lambda: self.delete_requested.emit(self.data))
        menu.addAction(
            "Открыть папку в проводнике",
            lambda: self.open_folder_requested.emit(self.data["path"])
        )
        menu.addSeparator()
        menu.addAction("Сменить превью...", lambda: self.set_preview_requested.emit(self.data))

        has_custom = self._has_custom_preview()
        reset_action = menu.addAction("Сбросить превью", lambda: self.reset_preview_requested.emit(self.data))
        reset_action.setEnabled(has_custom)

        menu.exec(QCursor.pos())

    def _has_custom_preview(self) -> bool:
        path = self.data.get("path", "")
        return bool(path and find_custom_preview(path))


class ProjectGrid(QWidget):
    projectClicked = Signal(dict)
    renameRequested = Signal(dict)
    deleteRequested = Signal(dict)
    openFolderRequested = Signal(str)
    setPreviewRequested = Signal(dict)
    resetPreviewRequested = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._grid = QGridLayout(self)
        self._grid.setSpacing(18)
        self._grid.setContentsMargins(0, 0, 0, 0)

        self._cards: list[ProjectCard] = []
        self._loader: PreviewLoaderThread | None = None

    def populate(self, projects: list):
        self._stop_loader()
        self._clear_cards()

        if not projects:
            label = QLabel("В рабочей папке нет проектов")
            label.setAlignment(Qt.AlignCenter)
            self._grid.addWidget(label, 0, 0)
            return

        cols = 4
        preview_paths: list[str] = []

        for i, proj in enumerate(projects):
            card = ProjectCard(proj, self)
            card.clicked.connect(self.projectClicked.emit)
            card.rename_requested.connect(self.renameRequested.emit)
            card.delete_requested.connect(self.deleteRequested.emit)
            card.open_folder_requested.connect(self.openFolderRequested.emit)
            card.set_preview_requested.connect(self.setPreviewRequested.emit)
            card.reset_preview_requested.connect(self.resetPreviewRequested.emit)

            self._grid.addWidget(card, i // cols, i % cols)
            self._cards.append(card)

            if proj.get("preview"):
                preview_paths.append(proj["preview"])

        if preview_paths:
            self._loader = PreviewLoaderThread(
                preview_paths, ProjectCard.PREVIEW_SIZE, self
            )
            self._loader.preview_ready.connect(self._on_preview_ready)
            self._loader.start()

    def _on_preview_ready(self, path: str, pixmap: QPixmap):
        for card in self._cards:
            if card.data.get("preview") == path:
                card.set_preview_pixmap(pixmap)
                break

    def _stop_loader(self):
        if self._loader is not None:
            self._loader.preview_ready.disconnect()
            self._loader.quit()
            self._loader.wait(500)
            self._loader = None

    def _clear_cards(self):
        for i in reversed(range(self._grid.count())):
            item = self._grid.itemAt(i)
            widget = item.widget() if item else None
            if widget:
                self._grid.removeWidget(widget)
                widget.setParent(None)
                widget.deleteLater()
        self._cards.clear()


class ProjectManager(QWidget):
    projectOpened = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.settings = QSettings("MangaOCRApp", "ProjectManager")
        self.workspace_path: str | None = None
        self.all_projects: list[dict] = []
        self.current_path: str | None = None

        self._setup_ui()

        last_path = self.settings.value("last_workspace", "")
        if last_path and os.path.isdir(last_path):
            self.workspace_path = last_path
            QTimer.singleShot(50, self.load_projects)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(16, 16, 16, 16)

        top_bar = QHBoxLayout()

        self.back_btn = QPushButton("← Назад")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setVisible(False)
        top_bar.addWidget(self.back_btn)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск проектов...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter_projects)

        self.choose_btn = QPushButton("Выбрать рабочую папку")
        self.choose_btn.clicked.connect(self.choose_workspace)

        top_bar.addWidget(self.search, 1)
        top_bar.addWidget(self.choose_btn)

        main_layout.addLayout(top_bar)

        title = QLabel("Проекты")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        main_layout.addWidget(title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.container = QWidget()
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        self.project_grid = ProjectGrid()
        container_layout.addWidget(self.project_grid)

        self.scroll.setWidget(self.container)
        main_layout.addWidget(self.scroll, 1)

        self.project_grid.projectClicked.connect(self.open_project)
        self.project_grid.renameRequested.connect(self.rename_project)
        self.project_grid.deleteRequested.connect(self.delete_project)
        self.project_grid.openFolderRequested.connect(self.open_in_explorer)
        self.project_grid.setPreviewRequested.connect(self.set_project_preview)
        self.project_grid.resetPreviewRequested.connect(self.reset_project_preview)

        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                self.set_workspace(path)
                return

    def choose_workspace(self):
        path = QFileDialog.getExistingDirectory(
            self, "Выберите рабочую папку",
            self.workspace_path or os.path.expanduser("~")
        )
        if path:
            self.set_workspace(path)

    def set_workspace(self, path: str):
        self.workspace_path = path
        self.current_path = None
        self.settings.setValue("last_workspace", path)
        self.load_projects()

    def _populate_from(self, folder: str, is_root: bool):
        try:
            projects = build_project_list(folder)
        except RuntimeError as e:
            QMessageBox.warning(self, "Ошибка", str(e))
            return

        self.all_projects = projects
        self.project_grid.populate(projects)

    def load_projects(self):
        if not self.workspace_path or not os.path.isdir(self.workspace_path):
            self.project_grid.populate([])
            return
        self._populate_from(self.workspace_path, is_root=True)

    def load_subdirs(self, path: str):
        self._populate_from(path, is_root=False)

    def go_back(self):
        try:
            ws_path = Path(self.workspace_path).resolve() if self.workspace_path else None

            if ws_path is None or not ws_path.is_dir():
                self._reset_to_root()
                return

            if self.current_path is None:
                self._reset_to_root()
                return

            cur_path = Path(self.current_path).resolve()

            if cur_path == ws_path or cur_path.parent == ws_path:
                self._reset_to_root()
                return

            parent_path = cur_path.parent
            if ws_path in parent_path.parents or parent_path == ws_path:
                self.load_subdirs(str(parent_path))
                self.current_path = str(parent_path)
                self.back_btn.setVisible(True)
                self.projectOpened.emit(str(parent_path))
                return

            self._reset_to_root()

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось вернуться назад:\n{e}")
            self._reset_to_root()

    def _reset_to_root(self):
        self.load_projects()
        self.current_path = None
        self.back_btn.setVisible(False)
        self.projectOpened.emit(self.workspace_path or "")

    def open_project(self, data: dict):
        if data.get("is_button"):
            self.choose_workspace()
            return

        project_path = data.get("path")
        if not project_path:
            return

        project_path = os.path.abspath(project_path)
        if not os.path.isdir(project_path):
            self.projectOpened.emit("")
            return

        self.current_path = project_path
        self.projectOpened.emit(project_path)

        has_subdirs = any(
            os.path.isdir(os.path.join(project_path, name))
            for name in os.listdir(project_path)
        )
        if has_subdirs:
            self.load_subdirs(project_path)
            self.back_btn.setVisible(True)
        else:
            self.back_btn.setVisible(
                self.current_path != self.workspace_path and self.workspace_path is not None
            )

    def create_image_list_widget(self, folder_path: str) -> QListWidget:
        list_widget = QListWidget()
        list_widget.setViewMode(QListWidget.IconMode)
        list_widget.setIconSize(QSize(120, 160))
        list_widget.setResizeMode(QListWidget.Adjust)
        list_widget.setSpacing(12)
        list_widget.setWordWrap(True)

        for file in sorted(os.listdir(folder_path)):
            if file.lower().endswith(IMAGE_EXTENSIONS_ALL):
                full_path = os.path.join(folder_path, file)
                pix = QPixmap(full_path).scaled(120, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                item = QListWidgetItem()
                item.setText(file)
                item.setData(Qt.UserRole, full_path)
                item.setIcon(QIcon(pix))
                list_widget.addItem(item)

        return list_widget

    def filter_projects(self):
        text = self.search.text().strip().lower()
        if not text:
            filtered = self.all_projects
        else:
            filtered = [
                p for p in self.all_projects
                if p.get("is_button") or text in p.get("name", "").lower()
            ]
        self.project_grid.populate(filtered)

    def rename_project(self, data: dict):
        old_name = data["name"]
        new_name, ok = QInputDialog.getText(
            self, "Переименование", "Новое название:", text=old_name
        )
        if not ok or not new_name or new_name == old_name:
            return

        old_path = data["path"]
        new_path = os.path.join(self.workspace_path, new_name)

        if os.path.exists(new_path):
            QMessageBox.warning(self, "Ошибка", "Такая папка уже существует!")
            return

        try:
            os.rename(old_path, new_path)
            self.load_projects()
        except OSError as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать:\n{e}")

    def delete_project(self, data: dict):
        name = data["name"]
        path = data["path"]

        reply = QMessageBox.question(
            self, "Удаление",
            f"Удалить проект «{name}» и все файлы внутри?\n\nЭто действие нельзя отменить.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            try:
                shutil.rmtree(path)
                self.load_projects()
            except OSError as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить проект:\n{e}")

    @staticmethod
    def open_in_explorer(path: str):
        if os.path.isdir(path):
            QDesktopServices.openUrl(Path(path).as_uri())

    def set_project_preview(self, data: dict):
        project_path = data.get("path", "")
        if not project_path:
            return

        image_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите превью",
            project_path,
            "Изображения (*.png *.jpg *.jpeg *.webp)"
        )
        if not image_path:
            return

        if set_custom_preview(project_path, image_path):
            self._reload_current_view()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось установить превью.")

    def reset_project_preview(self, data: dict):
        project_path = data.get("path", "")
        if not project_path:
            return
        remove_custom_preview(project_path)
        self._reload_current_view()

    def _reload_current_view(self):
        if self.current_path:
            self.load_subdirs(self.current_path)
        else:
            self.load_projects()
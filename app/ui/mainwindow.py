from pathlib import Path
from docx import Document
from PySide6.QtWidgets import (QMainWindow, QWidget, QListWidget, QVBoxLayout, QHBoxLayout, QLabel,
                               QSplitter, QToolBar, QFileDialog, QStatusBar, QGraphicsScene, QMenu)
from PySide6.QtGui import QPixmap, QAction, QPainter, QPen, QColor, QFont
from PySide6.QtCore import Qt, QPoint, QSettings, QSize, QTimer
from .jardic import JardicWidget
from .preview import ImageView
from .textexportpanel import TextExportPanel
from ..core.cahcefolder import CacheFolder
from ..core.cache import OCRCache
from ..core.utils import natural_key
from ..core.threads import ModelsLoadThread
from ..core.ocr import OCRThread, BatchThread
from ..ignore import ignore_warnings

ignore_warnings()

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".webp"}

class MainWindow(QMainWindow):
    __version__ = "Alpha 0.2.0"

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MangaOCR App")
        self.settings = QSettings("MangaOCR App")
        self.restore_window_state()

        self._create_actions()
        self._create_toolbar()
        self._create_central()
        self._create_statusbar()

        self.start_models_load()
        self.cache_folder = CacheFolder()

        self.mocr = None
        self.yolo_detector = None
        self.ocr_cache = OCRCache()
              
    def restore_window_state(self):
        size = self.settings.value("window_size", QSize(1000, 700), type=QSize)
        pos  = self.settings.value("window_pos", QPoint(100, 100), type=QPoint)

        self.resize(size)
        self.move(pos)

        was_maximized = self.settings.value("window_maximized", False, type=bool)
        if was_maximized:
            self.setWindowState(self.windowState() | Qt.WindowMaximized)

    def closeEvent(self, event):
        self.settings.setValue("window_maximized", self.isMaximized())

        if not self.isMaximized():
            self.settings.setValue("window_size", self.size())
            self.settings.setValue("window_pos", self.pos())

        super().closeEvent(event)

    def start_models_load(self):
        self.models_thread = ModelsLoadThread()
        self.models_thread.finished.connect(self.on_models_loaded)
        self.models_thread.error.connect(lambda e: print("Ошибка загрузки моделей:", e))
        self.models_thread.start()

    def on_models_loaded(self, mocr, yolo):
        self.mocr = mocr
        self.yolo_detector = yolo
        self.statusBar().showMessage("Модели успешно загружены")

    def _create_actions(self):
        self.open_folder_act = QAction("Открыть папку", self)
        self.open_folder_act.setShortcut("Ctrl+O")
        self.open_folder_act.triggered.connect(self.action_open_folder)

        self.recent_menu = QMenu(self)
        self.recent_menu.aboutToShow.connect(self.update_recent_menu)
        self.open_folder_act.setMenu(self.recent_menu)

        self.show_frames_act = QAction("Отображение", self)

        self.show_frames_menu = QMenu(self)
        self.show_frames_toggle = QAction("Фреймы", self, checkable=True)
        self.show_frames_toggle.setChecked(False)
        self.show_frames_toggle.triggered.connect(self.toggle_show_frames)

        self.show_frames_menu.addAction(self.show_frames_toggle)
        self.show_frames_act.setMenu(self.show_frames_menu)

        self.jardic_act = QAction("Jardic", self)
        self.jardic_act.setCheckable(True)
        self.jardic_act.setShortcut("J")
        self.jardic_act.triggered.connect(
            lambda checked=False: getattr(self, 'jardic_widget', None)
            .toggle(getattr(self, 'splitter', None), checked)
        )
        self.batch_act = QAction("Обработать всё", self)
        self.batch_act.triggered.connect(self.action_batch_process)

        self.export_act = QAction("Сохранить как...", self)
        self.export_act.triggered.connect(self.action_export_text)

        self.previous_image_act = QAction("Предыдущее изображение", self)
        self.previous_image_act.setShortcut("Up")
        self.previous_image_act.triggered.connect(self.previous_image)
        self.addAction(self.previous_image_act)

        self.next_image_act = QAction("Следующее изображение", self)
        self.next_image_act.setShortcut("Down")
        self.next_image_act.triggered.connect(self.next_image)
        self.addAction(self.next_image_act)
        
    def _create_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)

        self.addToolBar(tb)

        tb.addAction(self.open_folder_act)
        tb.addAction(self.show_frames_act)
        tb.addAction(self.jardic_act)
        tb.addAction(self.batch_act)
        tb.addAction(self.export_act)

    def _create_central(self):
        container = QWidget()
        self.setCentralWidget(container)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.setMinimumWidth(300)
        splitter.addWidget(self.list_widget)

        preview_container = QWidget()
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(4, 4, 4, 4)
        self.scene = QGraphicsScene()
        self.preview_view = ImageView()
        self.preview_view.setScene(self.scene)
        self.preview_view.setAlignment(Qt.AlignCenter)
        self.preview_view.setMinimumSize(200, 200)
        self.preview_view.setStyleSheet("background: #222; color: #eee; border: 1px solid #444;")
        preview_layout.addWidget(self.preview_view)
        splitter.addWidget(preview_container)
        self.splitter = splitter
        self.text_export_panel = TextExportPanel()
        self.text_export_panel.setMinimumWidth(250)
        splitter.addWidget(self.text_export_panel)
        self.jardic_widget = JardicWidget(self)
        try:
            self.jardic_widget.attach_to_splitter(self.splitter)
        except Exception:
            pass

        try:
            self.splitter.setSizes([300, 800, 250, 1])
        except Exception:
            pass

        try:
            splitter.setStretchFactor(0, 0)
            splitter.setStretchFactor(1, 1)
            splitter.setStretchFactor(2, 0)
            splitter.setStretchFactor(3, 0)
        except Exception:
            try:
                for i in range(splitter.count()):
                    splitter.setStretchFactor(i, 1 if i == 1 else 0)
            except Exception:
                pass

        self.current_folder = None
        self.entries = [] 

    def _create_statusbar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        status = self.statusBar()

        self.version_label = QLabel(self.__version__)
        self.version_label.setStyleSheet("color: gray; padding-right: 10px;")
        sb.addPermanentWidget(self.version_label)

    def action_open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с изображениями")
        if folder: 
            self.cache_folder.add(Path(folder))
            self.load_folder(Path(folder))

    def toggle_show_frames(self, checked):
        self.show_frames = checked
        current_index = self.list_widget.currentRow()
        if current_index >= 0:
            self.show_preview(
                self.entries[current_index],
                boxes=getattr(self, 'text_boxes', None),
                frames=getattr(self, 'frames', None)
            )

    def update_recent_menu(self):
        self.recent_menu.clear()
        folders = self.cache_folder.get_all()
        if not folders:
            self.recent_menu.addAction("(пусто)").setEnabled(False)
        else:
            for path in folders:
                act = self.recent_menu.addAction(str(path))
                act.triggered.connect(lambda checked=False, p=path: self.load_folder(p))
            self.recent_menu.addSeparator()

    def load_folder(self, folder: Path):
        if not folder.exists() or not folder.is_dir():
            self.statusBar().showMessage("Папка не существует")
            return

        self.current_folder = folder
        self.entries = [
            p for p in sorted(folder.iterdir(), key=lambda x: natural_key(x.name))
            if p.suffix.lower() in IMAGE_EXTENSIONS
        ]

        self.list_widget.clear()
        for p in self.entries:
            self.list_widget.addItem(p.name)

        self.statusBar().showMessage(f"Загружено из папки {folder}")

    def on_item_clicked(self, item):
        if self.yolo_detector is None:
            self.statusBar().showMessage("Модели ещё не загружены. Пожалуйста, подождите.")
            return

        idx = self.list_widget.row(item)
        if idx < 0 or idx >= len(self.entries):
            return

        path = self.entries[idx]
        self.show_preview(path, reset_zoom=True) 

        self._current_image_token = object()
        if hasattr(self, 'ocr_cache'):
            try:
                cached = self.ocr_cache.get_for_path(path)
            except Exception:
                cached = None
            if cached:
                boxes, frames, md5 = cached
                self.text_boxes, self.frames = boxes, frames
                self.show_preview(path, boxes=self.text_boxes, frames=self.frames, reset_zoom=False)
                self.text_export_panel.set_boxes(self.text_boxes, frames=self.frames, path=self.entries[idx])
                return

        if hasattr(self, 'ocr_thread') and self.ocr_thread is not None:
            self.ocr_thread.quit()
            self.ocr_thread.wait()

        self.ocr_thread = OCRThread(self, path, token=self._current_image_token)
        self.ocr_thread.finished.connect(self.on_ocr_finished)
        self.ocr_thread.start()

    def next_image(self):
        current_index = self.list_widget.currentRow()
        if current_index < len(self.entries) - 1:
            self.list_widget.setCurrentRow(current_index + 1)
            self.on_item_clicked(self.list_widget.currentItem())

    def previous_image(self):
        current_index = self.list_widget.currentRow()
        if current_index > 0:
            self.list_widget.setCurrentRow(current_index - 1)
            self.on_item_clicked(self.list_widget.currentItem())

    def action_batch_process(self):
        self.batch_thread = BatchThread(self, self.entries, parent=self)

        self.batch_thread.item_started.connect(self._on_batch_item_started)
        self.batch_thread.item_finished.connect(self._on_batch_item_finished)
        self.batch_thread.all_done.connect(self._on_batch_done)

        self.batch_thread.start()

    def _on_batch_item_started(self, idx, path):
        self.list_widget.setCurrentRow(idx)
        self.statusBar().showMessage(f"Обрабатывается: {path} ({idx+1}/{len(self.entries)})")

    def _on_batch_item_finished(self, idx, result):
        boxes, frames = result
        self.text_boxes, self.frames = boxes, frames
        self.text_export_panel.set_boxes(boxes, frames=frames)
        self.show_preview(self.entries[idx], boxes=boxes, frames=frames, reset_zoom=False)
        self.statusBar().showMessage(f"Завершено: {self.entries[idx]} ({idx+1}/{len(self.entries)})")

    def _on_batch_done(self):
        self.statusBar().showMessage("Пакетная обработка завершена")

    def action_export_text(self):
        if not hasattr(self, 'ocr_cache') or not self.entries:
            self.statusBar().showMessage("Нет текста для экспорта. Сначала обработайте изображения.")
            return

        first_file = Path(self.entries[0])
        default_name = first_file.parent.name + ".docx"
        filename, _ = QFileDialog.getSaveFileName(self, "Сохранить текст", default_name, "Word Documents (*.docx)")
        if not filename:
            return

        doc = Document()

        for path in self.entries:
            cached = self.ocr_cache.get_for_path(path)
            if cached:
                boxes, frames, _ = cached
                text = "\n".join([box.text for box in boxes if box.text])
                doc.add_paragraph(f"{Path(path).name}")
                doc.add_paragraph(text)
                doc.add_paragraph("") 
        try:
            doc.save(filename)
            self.statusBar().showMessage(f"Текст успешно сохранён в {filename}")
        except Exception as e:
            self.statusBar().showMessage(f"Ошибка сохранения файла: {e}")

    def on_ocr_finished(self, boxes, frames, img_cv, token):
        if token is not None and hasattr(self, '_current_image_token') and token != self._current_image_token:
            return

        self.text_boxes = boxes
        self.frames = frames

        if hasattr(self, 'ocr_cache'):
            try:
                path = self.entries[self.list_widget.currentRow()]
                self.ocr_cache.set_for_path(path, boxes, frames)
            except Exception:
                pass

        self.show_preview(self.entries[self.list_widget.currentRow()], boxes=boxes, reset_zoom=False, frames=frames)
        self.text_export_panel.set_boxes(boxes, frames=frames)

    def show_preview(self, path: Path, boxes=None, frames=None, reset_zoom=False):
        self.preview_view.text_boxes = boxes
        
        try:
            pixmap_to_show = QPixmap(str(path))
            with QPainter(pixmap_to_show) as painter:
                if frames and getattr(self, 'show_frames', False):
                    for f in frames:
                        rect = getattr(f, 'rect', f)
                        pen = QPen(QColor(0, 200, 0, 180), 3)
                        painter.setPen(pen)
                        painter.setBrush(QColor(0, 200, 0, 40))
                        painter.drawRect(rect)
                
                if boxes:
                    for box in boxes:
                        pen = QPen(QColor(0, 160, 230, 180), 3)
                        painter.setPen(pen)
                        painter.setBrush(QColor(0, 160, 230, 40))
                        painter.drawRect(box.rect)
                        rect = box.rect.adjusted(2, 2, -2, -2)
                        metrics = painter.fontMetrics()
                        elided_text = metrics.elidedText(box.text, Qt.ElideRight, rect.width())
                        painter.drawText(rect.topLeft() + QPoint(2, metrics.ascent() + 2), elided_text)

                if getattr(self, 'current_pixmap_item', None):
                    self.current_pixmap_item.setPixmap(pixmap_to_show)
                else:
                    self.current_pixmap_item = self.scene.addPixmap(pixmap_to_show)

                try:
                    self.scene.setSceneRect(pixmap_to_show.rect())
                except Exception:
                    pass

                if reset_zoom:
                    try:
                        self.preview_view._fit_enabled = True
                        self.preview_view._zoom = 1.0
                    except Exception:
                        pass
                    self.preview_view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)

                self.last_pixmap_for_cache = pixmap_to_show
                self.statusBar().showMessage(str(path))

        except Exception as e:
            self.statusBar().showMessage(f"Ошибка отображения превью: {e}")
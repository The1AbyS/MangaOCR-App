import os
import cv2
import copy
import torch
import json
import numpy as np
from .core.threads import ModelLoadThread, resource_path
from .core.utils import MangaTextBox, ImageItem, natural_key, pixmap_to_cv
from .core.cache import OCRCache, pixmap_md5
from .core.ocr import OCRThread
from .ui.styles import *
from .ui.widgets import TitleBar, SmoothListWidget, TextExportPanel
from .ui.hotkeys import handle_hotkeys
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QToolButton, QMenu, QAction,
                             QFileDialog, QListWidgetItem, QHBoxLayout, QProgressBar,
                             QGroupBox, QGraphicsOpacityEffect, QScroller, QAbstractItemView, QSizePolicy)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QImage, QCursor, QFont, QIcon, QPainterPath, QMouseEvent
from PyQt5.QtCore import (Qt, QRect, QPoint, QTimer, QPropertyAnimation, QEasingCurve, QUrl, QEvent, pyqtSlot)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PIL import Image
__version__ = "Alpha 0.1.0"

class MangaOCRApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setup_focus()
        self.init_state()
        self.init_mangaocr()
        self.setup_window()
        self.init_ui()

    def setup_focus(self):
        self.setFocusPolicy(Qt.StrongFocus)
        self.setFocus()
        QApplication.instance().installEventFilter(self)

    def init_state(self):
        self.mocr = None
        self.ocr_cache = OCRCache()

        self.all_text_boxes = []
        self.image_list = []
        self.current_image_path = None
        self.text_boxes = []
        self.history = []
        self.box_start = None
        self.box_end = None

    def init_mangaocr(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.start_mangaocr_load()

    def setup_window(self):
        screen = QApplication.primaryScreen()
        rect = screen.availableGeometry()
        width = int(rect.width() * 0.8)
        height = int(rect.height() * 0.8)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("MainWindowBg")
        self.setStyleSheet(mainbg_stylesheet + dark_stylesheet)
        self.setWindowTitle("MangaOCR App")
        self.setGeometry(100, 100, width, height)
        self.setMinimumSize(int(width * 0.6), int(height * 0.6))
        self.setAcceptDrops(True)

    def start_mangaocr_load(self):
        def load_mangaocr():
            from manga_ocr import MangaOcr
            model_dir = resource_path(os.path.join("..", "..", "models", "model_manga_ocr"))
            return MangaOcr(pretrained_model_name_or_path=model_dir)

        self.mangaocr_thread = ModelLoadThread(load_mangaocr)
        self.mangaocr_thread.finished.connect(self.on_mangaocr_loaded)
        self.mangaocr_thread.error.connect(lambda msg: self.notification(f"Ошибка загрузки MangaOCR: {msg}"))
        self.mangaocr_thread.start()

    def on_mangaocr_loaded(self, model):
        self.mocr = model
        self.auto_load_images()
        self.notification("MangaOCR модель загружена!")
    
    def auto_load_images(self):
        input_dir = os.path.join(os.path.dirname(__file__), "..", "input")
        if os.path.isdir(input_dir):
            self.image_list = [
                ImageItem(path=os.path.join(input_dir, f))
                for f in sorted(os.listdir(input_dir), key=natural_key)
                if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp')) and
                self.is_manga_page(os.path.join(input_dir, f))
            ]
            self.image_list_widget.clear()
            for image_item in self.image_list:
                if image_item.path:
                    pixmap = QPixmap(image_item.path)
                    item = QListWidgetItem(os.path.basename(image_item.path))
                    item.setIcon(QIcon(pixmap))
                elif image_item.pixmap:
                    item = QListWidgetItem(image_item.name or "Загружено")
                    item.setIcon(QIcon(image_item.pixmap))
                item.setData(Qt.UserRole, image_item)
                self.image_list_widget.addItem(item)
            if self.image_list:
                first_item_widget = self.image_list_widget.item(0)
                if first_item_widget:
                    self.load_selected_image(first_item_widget)  

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect()
        painter.setBrush(QColor("#121212"))
        painter.setPen(QColor("#222"))
        painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), 20, 20)

        path = QPainterPath()
        radius = 20
        bar_height = 40 
        w = rect.width()
        h = bar_height

        path.moveTo(0, h)
        path.lineTo(0, radius)
        path.quadTo(0, 0, radius, 0)
        path.lineTo(w - radius, 0)
        path.quadTo(w, 0, w, radius)
        path.lineTo(w, h)
        path.closeSubpath()

        painter.setBrush(QColor("#1f1f1f"))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = TitleBar(self)
        main_layout.addWidget(self.title_bar)

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(24)

        left_panel_widget = QWidget()
        left_panel_widget.setFixedWidth(350) 
        left_panel_widget.setStyleSheet("background: transparent;")

        left_panel = QVBoxLayout(left_panel_widget)
        left_panel.setContentsMargins(0, 0, 0, 0)
        left_panel.setSpacing(10)

        folder_clipboard_row = QHBoxLayout()
        folder_clipboard_row.setSpacing(8)

        self.btn_select_folder = QPushButton()
        self.btn_select_folder.setIcon(QIcon("icons/folder.svg"))
        self.btn_select_folder.setToolTip("Открыть папку с изображениями")
        self.btn_select_folder.setMinimumHeight(38)
        self.btn_select_folder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_select_folder.clicked.connect(self.select_folder)
        self.btn_select_folder.setStyleSheet(btn_select_folder_stylesheet)
        self.btn_yolo_model = QToolButton()
        self.btn_yolo_model.setText("M")
        self.btn_yolo_model.setToolTip("Выбрать YOLO модель")
        self.btn_yolo_model.setMinimumHeight(38)
        self.btn_yolo_model.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_yolo_model.setPopupMode(QToolButton.InstantPopup)
        self.btn_yolo_model.setStyleSheet(btn_yolo_model_stylesheet)

        self.yolo_menu = QMenu()
        self.yolo_menu.setStyleSheet(yolo_menu_stylesheet)
        self.yolo_models = {
            "N": "../models/yoloModels/yolo_n.pt",
            "S": "../models/yoloModels/yolo_s.pt",
            "M": "../models/yoloModels/yolo_m.pt",
            "L": "../models/yoloModels/yolo_l.pt",
        }
        for label, path in self.yolo_models.items():
            action = QAction(label, self)
            action.triggered.connect(lambda checked, l=label, p=path: self.set_yolo_model(l, p))
            self.yolo_menu.addAction(action)
        self.btn_yolo_model.setMenu(self.yolo_menu)

        self.yolo_model_path = self.yolo_models["M"]
        self.yolo_detector = None
        self.load_selected_yolo_model()

        self.btn_clear = QPushButton()
        self.btn_clear.setIcon(QIcon("icons/clean.svg"))
        self.btn_clear.setToolTip("Очистить весь список изображений")
        self.btn_clear.setMinimumHeight(38)
        self.btn_clear.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_clear.clicked.connect(self.clear_images)
        self.btn_clear.setStyleSheet(btn_clear_stylesheet)

        self.btn_jardic = QPushButton()
        self.btn_jardic.setIcon(QIcon("icons/jardic.png")) 
        self.btn_jardic.setToolTip("Открыть Jardic")
        self.btn_jardic.setMinimumHeight(38)
        self.btn_jardic.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_jardic.clicked.connect(self.toggle_jardic_browser)
        self.btn_jardic.setStyleSheet(btn_jardic_stylesheet)

        folder_clipboard_row.addWidget(self.btn_select_folder)
        folder_clipboard_row.addWidget(self.btn_clear)
        folder_clipboard_row.addWidget(self.btn_yolo_model)
        folder_clipboard_row.addWidget(self.btn_jardic)  
        left_panel.addLayout(folder_clipboard_row)

        self.image_list_widget = SmoothListWidget()
        self.image_list_widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        QScroller.grabGesture(self.image_list_widget.viewport(), QScroller.LeftMouseButtonGesture)

        self.image_list_widget.setFocusPolicy(Qt.StrongFocus)
        self.image_list_widget.setMinimumWidth(0)
        self.image_list_widget.setMaximumWidth(16777215)
        self.image_list_widget.setSpacing(5)
        self.image_list_widget.itemClicked.connect(self.load_selected_image)
        self.image_list_widget.verticalScrollBar().setStyleSheet(image_list_widget_stylesheet)

        left_panel.addWidget(self.image_list_widget)

        self.toggle_panel_buttons_layout = QHBoxLayout()
        self.btn_toggle_settings = QPushButton("О программе ▲")
        self.btn_toggle_group = QPushButton("Текст ▲")

        for btn in (self.btn_toggle_settings, self.btn_toggle_group):
            btn.setFixedHeight(30)
            btn.setStyleSheet(satting_and_group_stylesheet)
        self.toggle_panel_buttons_layout.addWidget(self.btn_toggle_settings)
        self.toggle_panel_buttons_layout.addWidget(self.btn_toggle_group)

        self.settings_group_panel = QGroupBox()
        self.settings_group_panel.setStyleSheet(settings_group_panel_stylesheet)
        self.settings_group_panel.setMaximumHeight(0)  
        self.settings_group_panel.setTitle("")
        self.settings_group_panel_layout = QVBoxLayout()
        self.settings_group_panel.setLayout(self.settings_group_panel_layout)

        self.settings_content = QWidget()
        self.settings_content.setLayout(QVBoxLayout())

        about_label = QLabel(
            f"""<b>Устройство обработки</b>: {self.device}<br><br>
        <tt>Часть горячих клавиш не работает из-за того, что я их пока удалил ^^</tt><br>
        <b>Горячие клавиши:</b><br>
        <tt>Ctrl + O</tt>: открыть папку с изображениями<br>
        <tt>Ctrl + V</tt>: вставить из буфера обмена (распознаёт папки, ссылки на главы с Rawkuma и просто изображения)<br>
        <tt>Ctrl + S</tt>: сохранить текстовый результат<br>
        <tt>Ctrl + R</tt>: очистить кэш<br>
        <tt>Ctrl + L</tt>: очистить список изображений<br>
        <tt>Ctrl + Z</tt>: отмена<br>
        <tt>J</tt>: открыть/закрыть Jardic<br>
        <tt>A</tt>: добавление боксов<br>
        <tt>D</tt>: удаление боксов<br>
        <tt>Q/E, стрелки вверх/вниз</tt>: перелистывание сканов<br><br>
        <b>Работа с изображением:</b><br>
        <tt>ЛКМ</tt>: скопировать текст в буфер обмена<br>
        <tt>ПКМ</tt>: вставить в поле Jardic<br><br>
        <b>Версия: {__version__}</b><br><br>
        """
        )
        about_label.setWordWrap(True)
        about_label.setTextFormat(Qt.RichText)
        about_label.setOpenExternalLinks(True)
        self.settings_content.layout().addWidget(about_label)

        self.group_content = TextExportPanel(self)

        left_panel.addLayout(self.toggle_panel_buttons_layout)
        left_panel.addWidget(self.settings_group_panel)

        self.panel_anim = QPropertyAnimation(self.settings_group_panel, b"maximumHeight")
        self.panel_anim.setDuration(350)
        self.panel_anim.setEasingCurve(QEasingCurve.InOutCubic)

        self.current_panel = None

        self.btn_toggle_settings.clicked.connect(lambda: self.toggle_panel("settings"))
        self.btn_toggle_group.clicked.connect(lambda: self.toggle_panel("group"))

        self.image_label = QLabel()
        self.image_label.setObjectName("image_label")
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(800, 700)
        self.image_label.setMouseTracking(True)
        self.image_label.mouseMoveEvent = self.on_mouse_move
        self.image_label.mousePressEvent = self.on_mouse_click
        self.image_label.setToolTip("")
        self.image_label.mousePressEvent = self.wrap_mouse_event(self.image_label.mousePressEvent, self.on_mouse_press_add_box)
        self.image_label.mouseMoveEvent = self.wrap_mouse_event(self.image_label.mouseMoveEvent, self.on_mouse_move_add_box)
        self.image_label.mouseReleaseEvent = self.wrap_mouse_event(self.image_label.mouseReleaseEvent, self.on_mouse_release_add_box)

        self.hovered_text = QLabel(self.image_label)
        self.hovered_text.setObjectName("hovered_text")
        self.hovered_text.setStyleSheet(hovered_text_stylesheet)
        self.hovered_text.hide()

        self.hovered_img_block = QLabel(self.image_label)
        self.hovered_img_block.setObjectName("hovered_img_block")
        self.hovered_img_block.setStyleSheet(hovered_img_block_stylesheet)
        self.hovered_img_block.hide()

        self.ocr_progress = QProgressBar(self)
        self.ocr_progress.setMinimum(0)
        self.ocr_progress.setMaximum(100)
        self.ocr_progress.setValue(0)
        self.ocr_progress.setAlignment(Qt.AlignCenter)
        self.ocr_progress.setVisible(False)
        self.ocr_progress.setFixedSize(220, 26)
        self.ocr_progress.setStyleSheet(ocr_progress_stylesheet)

        self.jardic_browser = QWebEngineView()
        self.jardic_browser.setUrl(QUrl("https://jardic.ru/"))
        self.jardic_browser.setVisible(False)
        self.jardic_browser.setMinimumWidth(400)
        self.jardic_browser.setStyleSheet(jardic_browser_stylesheet)
        self.jardic_browser.loadFinished.connect(lambda ok: self.setup_jardic_style())

        self.jardic_wrapper = QWidget()
        wrapper_layout = QVBoxLayout(self.jardic_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(self.jardic_browser)

        right_panel_widget = QWidget()
        right_panel_widget.setStyleSheet("background: transparent;")

        right_panel = QHBoxLayout(right_panel_widget)
        right_panel.setContentsMargins(0, 0, 0, 0)
        right_panel.setSpacing(12)
        self.right_panel = right_panel 

        right_image_layout = QVBoxLayout()
        right_image_layout.addWidget(self.image_label)
        right_image_layout.addStretch(1)

        right_panel.addLayout(right_image_layout, 1) 

        content_layout.addWidget(left_panel_widget, 0)  
        content_layout.addWidget(right_panel_widget, 1) 
        left_panel.setContentsMargins(0, 0, 0, 0)
        right_panel.setContentsMargins(0, 0, 0, 0)

        main_layout.addLayout(content_layout)

        self.add_box_mode = False
        self.delete_box_mode = False

        self.btn_add_box = QPushButton("+", self.image_label)
        self.btn_add_box.setFixedSize(38, 38)
        self.btn_add_box.setStyleSheet(btn_add_box_stylesheet)
        self.btn_add_box.setToolTip("Добавить бокс")
        self.btn_add_box.clicked.connect(self.enable_add_box_mode)

        self.btn_del_box = QPushButton("-", self.image_label)
        self.btn_del_box.setFixedSize(38, 38)
        self.btn_del_box.setStyleSheet(btn_del_box_stylesheet)
        self.btn_del_box.setToolTip("Удалить бокс")
        self.btn_del_box.clicked.connect(self.enable_del_box_mode)

        self.btn_prev = QPushButton("↑", self.image_label)
        self.btn_prev.setFixedSize(38, 38)
        self.btn_prev.setStyleSheet(btn_prev_stylesheet)
        self.btn_prev.setToolTip("Предыдущее изображение")
        self.btn_prev.clicked.connect(self.show_prev_image)

        self.btn_next = QPushButton("↓", self.image_label)
        self.btn_next.setFixedSize(38, 38)
        self.btn_next.setStyleSheet(btn_next_stylesheet)
        self.btn_next.setToolTip("Следующее изображение")
        self.btn_next.clicked.connect(self.show_next_image)

        self.btn_zoom_block = QPushButton("×0", self.image_label)
        self.btn_zoom_block.setFixedSize(38, 38)
        self.btn_zoom_block.setStyleSheet(btn_zoom_block_stylesheet)
        self.btn_zoom_block.setToolTip("Увеличить превью блока (выкл/×2/×3)")
        self.btn_zoom_block.clicked.connect(self.toggle_zoom_block_mode)
        self.zoom_block_mode = 0 

        def position_box_buttons():
            label_size = self.image_label.size()
            pixmap = self.image_label.pixmap()
            if pixmap is None:
                return
            pixmap_size = pixmap.size()

            scaled_w = min(label_size.width(), pixmap_size.width())
            scaled_h = min(label_size.height(), pixmap_size.height())

            offset_x = (label_size.width() - scaled_w) // 2
            offset_y = (label_size.height() - scaled_h) // 2

            btn_w = self.btn_add_box.width()
            btn_h = self.btn_add_box.height()
            space = 12
            total_h = btn_h * 5 + space * 4 

            y0 = offset_y + (scaled_h - total_h) // 2
            x0 = max(offset_x - btn_w - 16, 8)

            self.btn_add_box.move(x0, y0)
            self.btn_del_box.move(x0, y0 + btn_h + space)
            self.btn_zoom_block.move(x0, y0 + (btn_h + space) * 2)
            self.btn_prev.move(x0, y0 + (btn_h + space) * 3)
            self.btn_next.move(x0, y0 + (btn_h + space) * 4)
        self.position_box_buttons = position_box_buttons
        self.position_box_buttons()

    def show_prev_image(self):
        idx = self.image_list_widget.currentRow()
        if idx > 0:
            self.image_list_widget.setCurrentRow(idx - 1)
            self.load_selected_image(self.image_list_widget.item(idx - 1))

    def show_next_image(self):
        idx = self.image_list_widget.currentRow()
        if idx < self.image_list_widget.count() - 1:
            self.image_list_widget.setCurrentRow(idx + 1)
            self.load_selected_image(self.image_list_widget.item(idx + 1))

    def enable_add_box_mode(self):
        if self.add_box_mode:
            self.add_box_mode = False
            self.btn_add_box.setStyleSheet(btn_add_box_disabled_stylesheet)
            self.notification("Режим добавления боксов выключен")
        else:
            self.add_box_mode = True
            self.delete_box_mode = False
            self.btn_add_box.setStyleSheet(btn_add_box_enabled_stylesheet)
            self.btn_del_box.setStyleSheet(btn_del_box_disabled_stylesheet)
            self.notification("Режим добавления боксов включен")

    def enable_del_box_mode(self):
        if self.delete_box_mode:
            self.delete_box_mode = False
            self.btn_del_box.setStyleSheet(btn_del_box_disabled_stylesheet)
            self.notification("Режим удаления боксов выключен")
        else:
            self.delete_box_mode = True
            self.add_box_mode = False
            self.btn_del_box.setStyleSheet(btn_del_box_enabled_stylesheet)
            self.btn_add_box.setStyleSheet(btn_add_box_disabled_stylesheet)
            self.notification("Режим удаления боксов включен")

    def toggle_zoom_block_mode(self):
        self.zoom_block_mode = (self.zoom_block_mode + 1) % 3
        if self.zoom_block_mode == 0:
            self.btn_zoom_block.setText("×0")
            self.btn_zoom_block.setToolTip("Увеличить превью блока (выкл)")
        elif self.zoom_block_mode == 1:
            self.btn_zoom_block.setText("×2")
            self.btn_zoom_block.setToolTip("Увеличить превью блока (×2)")
        elif self.zoom_block_mode == 2:
            self.btn_zoom_block.setText("×3")
            self.btn_zoom_block.setToolTip("Увеличить превью блока (×3)")

        global_pos = QCursor.pos()
        local_pos = self.image_label.mapFromGlobal(global_pos)
        fake_event = QMouseEvent(QEvent.MouseMove, local_pos, Qt.NoButton, Qt.NoButton, Qt.NoModifier)
        self.on_mouse_move(fake_event)

    def on_mouse_press_add_box(self, event):
        if self.add_box_mode and event.button() == Qt.LeftButton:
            self.box_start = event.pos()
            self.box_end = event.pos()

    def on_mouse_move_add_box(self, event):
        if self.add_box_mode and self.box_start:
            self.box_end = event.pos()
            self.display_image_with_temp_box()

    def on_mouse_release_add_box(self, event):
        if self.add_box_mode and event.button() == Qt.LeftButton and self.box_start:
            self.save_history()
            self.box_end = event.pos()
            rect = QRect(self.box_start, self.box_end).normalized()

            label_size = self.image_label.size()
            pixmap = self.image_label.pixmap()
            if pixmap is None:
                self.box_start = None
                self.box_end = None
                return
            pixmap_size = pixmap.size()

            offset_x = (label_size.width() - pixmap_size.width()) // 2
            offset_y = (label_size.height() - pixmap_size.height()) // 2

            x1 = rect.left() - offset_x
            y1 = rect.top() - offset_y
            x2 = rect.right() - offset_x
            y2 = rect.bottom() - offset_y

            scale_x = getattr(self, 'scale_x', pixmap_size.width() / pixmap_size.width())
            scale_y = getattr(self, 'scale_y', pixmap_size.height() / pixmap_size.height())
            orig_x1 = int(x1 / scale_x)
            orig_y1 = int(y1 / scale_y)
            orig_x2 = int(x2 / scale_x)
            orig_y2 = int(y2 / scale_y)

            new_rect = QRect(
                min(orig_x1, orig_x2),
                min(orig_y1, orig_y2),
                abs(orig_x2 - orig_x1),
                abs(orig_y2 - orig_y1)
            )

            image_item = None
            if self.current_image_path is not None:
                for item in self.image_list:
                    if item.path == self.current_image_path:
                        image_item = item
                        break
            elif self.image_list_widget.currentRow() >= 0:
                image_item = self.image_list[self.image_list_widget.currentRow()]
            img_cv = None
            if image_item and image_item.path:
                img_cv = self.imread_unicode(image_item.path)
            elif image_item and image_item.pixmap:
                img_cv = pixmap_to_cv(self.image_item.pixmap)
            if img_cv is not None:
                x, y, w, h = new_rect.x(), new_rect.y(), new_rect.width(), new_rect.height()
                crop_img = img_cv[y:y+h, x:x+w]
                if crop_img is not None and crop_img.size > 0 and self.mocr:
                    try:
                        pil_img = Image.fromarray(cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB))
                        text = self.mocr(pil_img)
                    except Exception:
                        text = ""
            self.text_boxes.append(MangaTextBox(new_rect, text))

            self.box_start = None
            self.box_end = None

            if img_cv is not None:
                self.display_image_with_boxes(img_cv)
            self.notification("Бокс добавлен!")

    def display_image_with_temp_box(self):
        img_cv = None
        if self.current_image_path:
            img_cv = cv2.imread(self.current_image_path)
        elif self.image_label.pixmap():
            img_cv = pixmap_to_cv(self.image_item.pixmap)
        if img_cv is None:
            return

        height, width, channel = img_cv.shape
        bytes_per_line = 3 * width
        qimage = QImage(img_cv.data, width, height, bytes_per_line, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(qimage)

        pixmap_with_boxes = QPixmap(pixmap)
        painter = QPainter(pixmap_with_boxes)
        font = QFont('Segoe UI', 10)
        painter.setFont(font)

        for box in self.text_boxes:
            pen = QPen(QColor(0, 160, 230, 180), 3)
            painter.setPen(pen)
            painter.setBrush(QColor(0, 160, 230, 40))
            painter.drawRect(box.rect)

        if self.add_box_mode and self.box_start and self.box_end:
            label_size = self.image_label.size()
            pixmap = self.image_label.pixmap()
            pixmap_size = pixmap.size()
            offset_x = (label_size.width() - pixmap_size.width()) // 2
            offset_y = (label_size.height() - pixmap_size.height()) // 2

            x1 = (self.box_start.x() - offset_x) / self.scale_x
            y1 = (self.box_start.y() - offset_y) / self.scale_y
            x2 = (self.box_end.x() - offset_x) / self.scale_x
            y2 = (self.box_end.y() - offset_y) / self.scale_y

            temp_rect = QRect(
                int(min(x1, x2)),
                int(min(y1, y2)),
                int(abs(x2 - x1)),
                int(abs(y2 - y1))
            )
            pen = QPen(QColor(255, 200, 0, 180), 2, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(temp_rect)

            painter.end()

        radius = 20
        rounded = QPixmap(pixmap_with_boxes.size())
        rounded.fill(Qt.transparent)
        mask_painter = QPainter(rounded)
        mask_painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, rounded.width(), rounded.height(), radius, radius)
        mask_painter.setClipPath(path)
        mask_painter.drawPixmap(0, 0, pixmap_with_boxes)
        mask_painter.end()

        scaled_pixmap = rounded.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        self.scale_x = scaled_pixmap.width() / width
        self.scale_y = scaled_pixmap.height() / height

    def toggle_delete_box_mode(self):
        self.delete_box_mode = self.btn_delete_box_mode.isChecked()
        if self.delete_box_mode:
            self.notification("Кликните по нужному боксу для удаления")
        else:
            self.notification("Режим удаления боксов выключен")

    def set_yolo_model(self, label, path):
        self.btn_yolo_model.setText(f"{label}")
        self.yolo_model_path = path
        self.clear_ocr_cache()
        self.load_selected_yolo_model()
        self.notification("Кэш OCR очищен из-за смены YOLO-модели!")

    def toggle_panel(self, panel_type):
        if self.current_panel == panel_type:
            self.panel_anim.stop()
            self.panel_anim.setStartValue(self.settings_group_panel.height())
            self.panel_anim.setEndValue(0)
            self.panel_anim.start()
            self.current_panel = None
            self.btn_toggle_settings.setText("О программе ▲")
            self.btn_toggle_group.setText("Текст ▲")
            return

        if self.current_panel is not None:
            self.panel_anim.stop()
            self.panel_anim.setStartValue(self.settings_group_panel.height())
            self.panel_anim.setEndValue(0)
            self.panel_anim.finished.connect(lambda: self._show_new_panel(panel_type))
            self.panel_anim.start()
        else:
            self._show_new_panel(panel_type)

    @pyqtSlot()
    def _show_new_panel(self, panel_type):
        try:
            self.panel_anim.finished.disconnect()
        except Exception:
            pass

        while self.settings_group_panel_layout.count():
            item = self.settings_group_panel_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        if panel_type == "settings":
            self.settings_group_panel_layout.addWidget(self.settings_content)
            end_height = self.settings_content.sizeHint().height() + 30
            self.btn_toggle_settings.setText("О программе ▼")
            self.btn_toggle_group.setText("Текст ▲")
        elif panel_type == "group":
            self.settings_group_panel_layout.addWidget(self.group_content)
            end_height = self.group_content.sizeHint().height() + 30
            self.btn_toggle_settings.setText("О программе ▲")
            self.btn_toggle_group.setText("Текст ▼")

        self.panel_anim.stop()
        self.panel_anim.setStartValue(0)
        self.panel_anim.setEndValue(end_height)
        self.panel_anim.start()
        self.current_panel = panel_type

    def save_history(self):
        self.history.append((
            list(self.image_list),
            self.current_image_path,
            copy.deepcopy(self.text_boxes)
        ))
        if len(self.history) > 100:
            self.history.pop(0)

    def undo_action(self):
        if not self.history:
            self.notification("Нет действий для отмены.")
            return
        prev_list, prev_path, prev_boxes = self.history.pop()
        self.image_list = prev_list
        self.current_image_path = prev_path
        self.text_boxes = prev_boxes
        self.image_list_widget.clear()
        for image_item in self.image_list:
            if image_item.path:
                pixmap = QPixmap(image_item.path)
                item = QListWidgetItem(os.path.basename(image_item.path))
                item.setIcon(QIcon(pixmap))
            elif image_item.pixmap:
                item = QListWidgetItem(image_item.name or "Загружено")
                item.setIcon(QIcon(image_item.pixmap))
            item.setData(Qt.UserRole, image_item)
            self.image_list_widget.addItem(item)
        if self.current_image_path and any(item.path == self.current_image_path for item in self.image_list):
            idx = next(i for i, item in enumerate(self.image_list) if item.path == self.current_image_path)
            self.image_list_widget.setCurrentRow(idx)
            if self.current_image_path:
                img_cv = self.imread_unicode(self.current_image_path)
                self.display_image_with_boxes(img_cv)
            elif self.image_list[idx].pixmap:
                img_cv = pixmap_to_cv(self.image_item.pixmap)
        else:
            self.image_label.clear()
            self.text_boxes = []

    def wrap_mouse_event(self, orig_event, custom_event):
        def wrapper(event):
            custom_event(event)
            orig_event(event)
        return wrapper
    
    def select_folder(self):
        input_dir = QFileDialog.getExistingDirectory(self, "Выбрать папку с изображениями")
        if input_dir:
            self.save_history()
            self.image_list = [
                ImageItem(path=os.path.join(input_dir, f))
                for f in sorted(os.listdir(input_dir), key=natural_key)
                if f.lower().endswith(('.jpg', '.png', '.jpeg', '.webp')) and
                self.is_manga_page(os.path.join(input_dir, f))
            ]
            self.image_list_widget.clear()
            for image_item in self.image_list:
                if image_item.path:
                    pixmap = QPixmap(image_item.path)
                    item = QListWidgetItem(os.path.basename(image_item.path))
                    item.setIcon(QIcon(pixmap))
                elif image_item.pixmap:
                    item = QListWidgetItem(image_item.name or "Загружено")
                    item.setIcon(QIcon(image_item.pixmap))
                item.setData(Qt.UserRole, image_item)
                self.image_list_widget.addItem(item)

    def load_selected_image(self, item):
        image_item = item.data(Qt.UserRole)
        if image_item is None:
            return
        self._current_image_token = object()

        if image_item.pixmap is not None:
            self.image_label.setPixmap(image_item.pixmap)
            self.current_image_path = None
        elif image_item.path is not None:
            pixmap = QPixmap(image_item.path)
            self.image_label.setPixmap(pixmap)
            self.current_image_path = image_item.path
        if hasattr(self, 'position_box_buttons'):
            self.position_box_buttons()
        self.text_boxes = []
        self.display_image_with_boxes_placeholder()

        if image_item.path:
            cache_key = image_item.path
        elif image_item.pixmap:
            cache_key = pixmap_md5(image_item.pixmap)
        else:
            cache_key = None

        if cache_key and cache_key in self.ocr_cache:
            self.text_boxes, img_cv = self.ocr_cache[cache_key]
            self.display_image_with_boxes(img_cv)
            return

        if hasattr(self, 'ocr_thread') and self.ocr_thread is not None:
            self.ocr_thread.quit()
            self.ocr_thread.wait()
        self.ocr_thread = OCRThread(self, image_item)
        self.ocr_thread.token = self._current_image_token
        self.ocr_thread.progress.connect(self.update_ocr_progress)
        self.ocr_thread.finished.connect(self.on_ocr_finished)
        self.ocr_progress.setValue(0)
        self.ocr_progress.setVisible(True)
        self.ocr_thread.start()

    def update_ocr_progress(self, current, total, token=None):
        if hasattr(self, '_current_image_token') and token is not None and token != self._current_image_token:
            return
        self.ocr_progress.setMaximum(total)
        self.ocr_progress.setValue(current)

    def imread_unicode(self, path):
        with open(path, 'rb') as f:
            data = f.read()
        img_array = np.frombuffer(data, np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img

    def detect_text_boxes(self, image_cv):
        if self.yolo_detector is not None:
            results = self.yolo_detector(image_cv, iou=0.05)
            boxes = []
            for r in results[0].boxes:
                if int(r.cls[0]) == 3:
                    x1, y1, x2, y2 = map(int, r.xyxy[0].cpu().numpy())
                    box = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]])
                    boxes.append(box)
            return boxes
    
    def group_and_recognize_lines(self, img_cv, boxes):
        text_boxes = []
        h_img, w_img = img_cv.shape[:2]
        for box in boxes:
            x, y, w, h = cv2.boundingRect(box)
            x = max(0, x)
            y = max(0, y)
            w = min(w, w_img - x)
            h = min(h, h_img - y)
            if w <= 0 or h <= 0:
                continue
            crop_img = img_cv[y:y+h, x:x+w]
            if crop_img is None or crop_img.size == 0:
                continue
            try:
                pil_img = Image.fromarray(cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB))
            except Exception:
                continue
            text = self.mocr(pil_img) if self.mocr else ""
            rect = QRect(x, y, w, h)
            text_boxes.append(MangaTextBox(rect, text))
        return text_boxes

    def highlight_box_by_line(self, idx):
        if 0 <= idx < len(self.text_boxes):
            self.highlighted_box_idx = idx

            if self.current_image_path:
                cache_key = self.current_image_path
            else:
                cache_key = pixmap_md5(self.last_pixmap_for_cache)
            
            if cache_key in self.ocr_cache:
                img_cv = self.ocr_cache[cache_key][1]  
                self.display_image_with_boxes(img_cv, highlight_idx=idx)

    def display_image_with_boxes_placeholder(self):
        pixmap = self.image_label.pixmap()
        if pixmap:
            radius = 20 
            rounded = QPixmap(pixmap.size())
            rounded.fill(Qt.transparent)

            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addRoundedRect(0, 0, rounded.width(), rounded.height(), radius, radius)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()

            scaled_pixmap = rounded.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            if hasattr(self, 'position_box_buttons'):
                self.position_box_buttons()

    def on_ocr_finished(self, text_boxes, img_cv, token=None):
        if hasattr(self, '_current_image_token') and token is not None and token != self._current_image_token:
            return

        self.ocr_progress.setVisible(False)
        self.text_boxes = text_boxes
        if img_cv is not None:
            self.display_image_with_boxes(img_cv)
        if self.current_image_path:
            cache_key = self.current_image_path
        elif hasattr(self, 'last_pixmap_for_cache'):
            cache_key = pixmap_md5(self.last_pixmap_for_cache)
        else:
            cache_key = None
        if cache_key:
            self.ocr_cache[cache_key] = (text_boxes, img_cv)
            
    def display_image_with_boxes(self, image_cv=None, pixmap=None, highlight_idx=None):
        if image_cv is None and pixmap is not None:
            image_cv = pixmap_to_cv(pixmap)
        elif image_cv is None:
            return

        height, width, channel = image_cv.shape
        bytes_per_line = 3 * width
        qimage = QImage(image_cv.data, width, height, bytes_per_line, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(qimage)

        self.last_pixmap_for_cache = pixmap
        pixmap_with_boxes = QPixmap(pixmap)

        painter = QPainter(pixmap_with_boxes)
        font = QFont('Segoe UI', 10)
        painter.setFont(font)

        for i, box in enumerate(self.text_boxes):
            if highlight_idx is not None and i == highlight_idx:
                pen = QPen(QColor(255, 80, 80, 220), 5)
                painter.setBrush(QColor(255, 80, 80, 40))
            else:
                pen = QPen(QColor(0, 160, 230, 180), 3)
                painter.setBrush(QColor(0, 160, 230, 40))
            painter.setPen(pen)
            painter.drawRect(box.rect)
            rect = box.rect.adjusted(2, 2, -2, -2)
            metrics = painter.fontMetrics()
            elided_text = metrics.elidedText(box.text, Qt.ElideRight, rect.width())
            painter.drawText(rect.topLeft() + QPoint(2, metrics.ascent() + 2), elided_text)

        painter.end()

        radius = 20
        rounded = QPixmap(pixmap_with_boxes.size())
        rounded.fill(Qt.transparent)

        mask_painter = QPainter(rounded)
        mask_painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, rounded.width(), rounded.height(), radius, radius)
        mask_painter.setClipPath(path)
        mask_painter.drawPixmap(0, 0, pixmap_with_boxes)
        mask_painter.end()

        scaled_pixmap = rounded.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled_pixmap)
        self.scale_x = scaled_pixmap.width() / width
        self.scale_y = scaled_pixmap.height() / height

        if hasattr(self, 'position_box_buttons'):
            self.position_box_buttons()

    def load_selected_yolo_model(self):
        from ultralytics import YOLO
        self.yolo_detector = YOLO(self.yolo_model_path)

    def on_mouse_move(self, event):
        pos = event.pos()

        if not hasattr(self, 'scale_x') or not hasattr(self, 'scale_y') or self.scale_x == 0 or self.scale_y == 0:
            self.hovered_text.hide()
            self.hovered_img_block.hide()
            return

        label_size = self.image_label.size()
        pixmap = self.image_label.pixmap()
        if pixmap is None:
            self.hovered_text.hide()
            self.hovered_img_block.hide()
            return
        pixmap_size = pixmap.size()

        offset_x = (label_size.width() - pixmap_size.width()) // 2
        offset_y = (label_size.height() - pixmap_size.height()) // 2

        x_in_pixmap = pos.x() - offset_x
        y_in_pixmap = pos.y() - offset_y

        if x_in_pixmap < 0 or y_in_pixmap < 0 or x_in_pixmap > pixmap_size.width() or y_in_pixmap > pixmap_size.height():
            self.hovered_text.hide()
            self.hovered_img_block.hide()
            return

        orig_x = x_in_pixmap / self.scale_x
        orig_y = y_in_pixmap / self.scale_y
        orig_pos = QPoint(int(orig_x), int(orig_y))

        for box in self.text_boxes:
            if box.rect.contains(orig_pos):
                if self.jardic_browser.isVisible():
                    image_label_global = self.image_label.mapToGlobal(QPoint(0, 0))
                    jardic_global = self.jardic_browser.mapToGlobal(QPoint(0, 0))
                    max_width = jardic_global.x() - image_label_global.x() - 30 
                    max_width = max(120, max_width)
                    self.hovered_text.setWordWrap(True)
                    self.hovered_text.setMaximumWidth(max_width)
                else:
                    self.hovered_text.setWordWrap(False)
                    self.hovered_text.setMaximumWidth(16777215)

                self.hovered_text.setText(box.text)
                self.hovered_text.adjustSize()

                img_cv = None
                if self.current_image_path:
                    img_cv = cv2.imread(self.current_image_path)
                elif self.image_label.pixmap():
                    img_cv = pixmap_to_cv(self.image_item.pixmap)
                crop = None
                if img_cv is not None:
                    x, y, w, h = box.rect.x(), box.rect.y(), box.rect.width(), box.rect.height()
                    crop = img_cv[y:y+h, x:x+w]
                    if crop is not None and crop.size > 0:
                        zoom = 1
                        if hasattr(self, 'zoom_block_mode'):
                            if self.zoom_block_mode == 1:
                                zoom = 2
                            elif self.zoom_block_mode == 2:
                                zoom = 3
                        if zoom > 1:
                            preview_w = int(w * zoom)
                            preview_h = int(h * zoom)
                            max_preview_w = 300
                            max_preview_h = 300
                            scale = min(max_preview_w / preview_w, max_preview_h / preview_h, 1.0)
                            preview_w = int(preview_w * scale)
                            preview_h = int(preview_h * scale)
                            crop_resized = cv2.resize(crop, (preview_w, preview_h), interpolation=cv2.INTER_AREA)
                            qimage = QImage(crop_resized.data, preview_w, preview_h, 3 * preview_w, QImage.Format_BGR888)
                            pixmap = QPixmap.fromImage(qimage)
                            self.hovered_img_block.setPixmap(pixmap)
                            self.hovered_img_block.setFixedSize(preview_w, preview_h)
                            self.hovered_img_block.show()
                            if self.jardic_browser.isVisible():
                                image_label_global = self.image_label.mapToGlobal(QPoint(0, 0))
                                jardic_global = self.jardic_browser.mapToGlobal(QPoint(0, 0))
                                max_width = jardic_global.x() - image_label_global.x() - 30
                                max_width = max(120, max_width)
                                self.hovered_text.setWordWrap(True)
                                self.hovered_text.setMaximumWidth(max_width)
                            else:
                                self.hovered_text.setWordWrap(False)
                                self.hovered_text.setMaximumWidth(16777215)
                        else:
                            self.hovered_img_block.hide()

                x = pos.x() + 15
                y = pos.y() + 15

                img_block_y = max(0, min(y - self.hovered_img_block.height(), self.image_label.height() - self.hovered_img_block.height()))
                self.hovered_img_block.move(x, img_block_y)
                self.hovered_text.move(x, y)
                self.hovered_text.show()
                return

        self.hovered_text.hide()
        self.hovered_img_block.hide()

    def notification(self, message):
        if not hasattr(self, 'copy_notification'):
            self.copy_notification = QLabel(self)
            self.copy_notification.setStyleSheet(copy_notification_stylesheet)
            self.copy_notification.setAlignment(Qt.AlignCenter)
            self.copy_notification.hide()

            self.copy_notification.opacity_effect = QGraphicsOpacityEffect(self.copy_notification)
            self.copy_notification.setGraphicsEffect(self.copy_notification.opacity_effect)

            self.copy_notification.fade_anim = QPropertyAnimation(self.copy_notification.opacity_effect, b"opacity")
            self.copy_notification.fade_anim.setDuration(300)
            self.copy_notification.fade_anim.setEasingCurve(QEasingCurve.InOutQuad)

            def on_fade_finished():
                if self.copy_notification.opacity_effect.opacity() < 0.05:
                    self.copy_notification.hide()

            self.copy_notification.fade_anim.finished.connect(on_fade_finished)

            self.copy_notification.hide_timer = QTimer()
            self.copy_notification.hide_timer.setSingleShot(True)
            self.copy_notification.hide_timer.timeout.connect(self._fade_out_notification)

        self.copy_notification.setText(message)
        self.copy_notification.adjustSize()

        x = self.width() - self.copy_notification.width() - 30
        y = self.height() - self.copy_notification.height() - 30
        self.copy_notification.move(x, y)

        if not self.copy_notification.isVisible():
            self.copy_notification.opacity_effect.setOpacity(0.0)
            self.copy_notification.show()
            self.copy_notification.fade_anim.stop()
            self.copy_notification.fade_anim.setStartValue(0.0)
            self.copy_notification.fade_anim.setEndValue(1.0)
            self.copy_notification.fade_anim.start()
        else:
            self.copy_notification.fade_anim.stop()
            self.copy_notification.opacity_effect.setOpacity(1.0)

        duration = max(1500, len(message) * 80)
        self.copy_notification.hide_timer.start(duration)

    def _fade_out_notification(self):
        if hasattr(self, 'copy_notification'):
            self.copy_notification.fade_anim.stop()
            self.copy_notification.fade_anim.setStartValue(1.0)
            self.copy_notification.fade_anim.setEndValue(0.0)
            self.copy_notification.fade_anim.start()

    def on_mouse_click(self, event):
        pos = event.pos()
        if self.delete_box_mode and event.button() == Qt.LeftButton:
            if not hasattr(self, 'scale_x') or not hasattr(self, 'scale_y') or self.scale_x == 0 or self.scale_y == 0:
                return

            label_size = self.image_label.size()
            pixmap = self.image_label.pixmap()
            if pixmap is None:
                return
            pixmap_size = pixmap.size()

            offset_x = (label_size.width() - pixmap_size.width()) // 2
            offset_y = (label_size.height() - pixmap_size.height()) // 2

            x_in_pixmap = pos.x() - offset_x
            y_in_pixmap = pos.y() - offset_y

            if x_in_pixmap < 0 or y_in_pixmap < 0 or x_in_pixmap > pixmap_size.width() or y_in_pixmap > pixmap_size.height():
                return

            orig_x = x_in_pixmap / self.scale_x
            orig_y = y_in_pixmap / self.scale_y
            orig_pos = QPoint(int(orig_x), int(orig_y))

            for i, box in enumerate(self.text_boxes):
                if box.rect.contains(orig_pos):
                    self.save_history()
                    del self.text_boxes[i]
                    img_cv = None
                    if self.current_image_path:
                        img_cv = cv2.imread(self.current_image_path)
                    elif self.image_label.pixmap():
                        img_cv = pixmap_to_cv(self.image_item.pixmap)
                    if img_cv is not None:
                        self.display_image_with_boxes(img_cv)
                    self.notification("Бокс удалён")
                    break
            return

        if event.button() == Qt.RightButton:
            if not hasattr(self, 'scale_x') or not hasattr(self, 'scale_y') or self.scale_x == 0 or self.scale_y == 0:
                return

            label_size = self.image_label.size()
            pixmap = self.image_label.pixmap()
            if pixmap is None:
                return
            pixmap_size = pixmap.size()

            offset_x = (label_size.width() - pixmap_size.width()) // 2
            offset_y = (label_size.height() - pixmap_size.height()) // 2

            x_in_pixmap = pos.x() - offset_x
            y_in_pixmap = pos.y() - offset_y

            if x_in_pixmap < 0 or y_in_pixmap < 0 or x_in_pixmap > pixmap_size.width() or y_in_pixmap > pixmap_size.height():
                return

            orig_x = x_in_pixmap / self.scale_x
            orig_y = y_in_pixmap / self.scale_y
            orig_pos = QPoint(int(orig_x), int(orig_y))

            for box in self.text_boxes:
                if box.rect.contains(orig_pos):
                    self.send_text_to_jardic(box.text)
                    break
            return

        if not hasattr(self, 'scale_x') or not hasattr(self, 'scale_y') or self.scale_x == 0 or self.scale_y == 0:
            return

        label_size = self.image_label.size()
        pixmap = self.image_label.pixmap()
        if pixmap is None:
            return
        pixmap_size = pixmap.size()

        offset_x = (label_size.width() - pixmap_size.width()) // 2
        offset_y = (label_size.height() - pixmap_size.height()) // 2

        x_in_pixmap = pos.x() - offset_x
        y_in_pixmap = pos.y() - offset_y

        if x_in_pixmap < 0 or y_in_pixmap < 0 or x_in_pixmap > pixmap_size.width() or y_in_pixmap > pixmap_size.height():
            return

        orig_x = x_in_pixmap / self.scale_x
        orig_y = y_in_pixmap / self.scale_y
        orig_pos = QPoint(int(orig_x), int(orig_y))

        for box in self.text_boxes:
            if box.rect.contains(orig_pos):
                QApplication.clipboard().setText(box.text)
                self.notification("Текст скопирован!")
                return
        
    def resizeEvent(self, event):
        if self.text_boxes:
            img_cv = None
            if self.current_image_path:
                img_cv = cv2.imread(self.current_image_path)
            elif self.image_label.pixmap():
                img_cv = pixmap_to_cv(self.image_item.pixmap)
            if img_cv is not None:
                self.display_image_with_boxes(img_cv)
        super().resizeEvent(event)
        if hasattr(self, 'ocr_progress') and hasattr(self, 'image_label'):
            label_pos = self.image_label.mapTo(self.ocr_progress.parentWidget(), QPoint(0, 0))
            x = label_pos.x() + (self.image_label.width() - self.ocr_progress.width()) // 2
            y = label_pos.y() + self.image_label.height() + 16
            self.ocr_progress.move(x, y)
        if hasattr(self, 'position_box_buttons'):
            self.position_box_buttons()
    
    def delete_selected_image(self):
        selected = self.image_list_widget.currentRow()
        if selected >= 0:
            self.save_history()
            del self.image_list[selected]
            self.image_list_widget.takeItem(selected)
            self.image_list_widget.setCurrentRow(-1) 

            if self.image_list:
                idx = min(selected, len(self.image_list) - 1)
                self.image_list_widget.setCurrentRow(idx)

                image = self.image_list[idx]

                if hasattr(image, "pixmap") and hasattr(image, "path"):
                    self.current_image = image.pixmap
                    self.current_image_path = image.path

                    if self.current_image:
                        self.image_label.setPixmap(self.current_image)
                    else:
                        self.image_label.clear()

                elif isinstance(image, QPixmap):
                    self.current_image = image
                    self.current_image_path = None
                    self.image_label.setPixmap(self.current_image)

                elif isinstance(image, str):
                    self.current_image_path = image
                    self.current_image = QPixmap(self.current_image_path)
                    self.image_label.setPixmap(self.current_image)

                else:
                    print(f"Неизвестный формат элемента: {image}")
                    self.image_label.clear()
            else:
                self.current_image = None
                self.current_image_path = None
                self.image_label.clear()
                self.text_boxes = []
                self.hovered_text.hide()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.KeyPress:
            handled = handle_hotkeys(self, event)
            if handled:
                return True
        return super().eventFilter(obj, event)

    def clear_images(self):
        self.notification("Удалено " + str(len(self.image_list)) + " изображений.")
        self.save_history() 
        self.image_list_widget.clear()
        self.image_list.clear()
        self.current_image_path = None
        self.image_label.clear()
        self.text_boxes = []
        self.hovered_text.hide()

    def setup_jardic_style(self):
        safe_css = json.dumps(jardic_css)  
        js = f"""
        (function() {{
            try {{
                // Скрываем ненужные элементы
                let header = document.querySelector('.section0');
                if (header) header.style.display = 'none';
                let footer = document.querySelector('footer');
                if (footer) footer.style.display = 'none';
                let form1 = document.querySelector('form[name="form1"]');
                if (form1) form1.style.display = 'none';

                // Вставляем стиль (уникальное имя переменной)
                let customStyle = document.createElement('style');
                customStyle.innerHTML = {safe_css};
                document.head.appendChild(customStyle);
            }} catch (e) {{
                console.error("Jardic style injection error:", e);
            }}
        }})();
        """
        self.jardic_browser.page().runJavaScript(js)

    def toggle_jardic_browser(self):
        visible = not self.jardic_browser.isVisible()
        self.jardic_browser.setVisible(visible)

        if visible:
            if self.right_panel.indexOf(self.jardic_wrapper) == -1:
                self.right_panel.addWidget(self.jardic_wrapper, 2)
            self.btn_jardic.setStyleSheet(btn_jardic_enabled_stylesheet)
        else:
            if self.right_panel.indexOf(self.jardic_wrapper) != -1:
                self.right_panel.removeWidget(self.jardic_wrapper)
                self.jardic_wrapper.setParent(None)
            self.btn_jardic.setStyleSheet(btn_jardic_disabled_stylesheet)
        if hasattr(self, 'position_box_buttons'):
            QTimer.singleShot(0, self.position_box_buttons)

    def send_text_to_jardic(self, text):
        if not self.jardic_browser.isVisible():
            self.toggle_jardic_browser()
        js = f"""
            var input = document.querySelector('input[name="q"]');
            if(input) {{
                input.value = "{text}";
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                var btn = document.querySelector('input[type="submit"][value="Найти"]');
                if(btn) btn.click();
            }}
        """
        self.jardic_browser.page().runJavaScript(js)
        if hasattr(self, 'position_box_buttons'):
            self.position_box_buttons()

    def is_manga_page(self, image_path):
        try:
            img = cv2.imread(image_path)
            if img is None:
                self.notification(f"Не удалось загрузить изображение")
                return False
            h, w = img.shape[:2]
            if w < 400 or h < 400: 
                self.notification(f"Изображение слишком маленькое, если это страница манги, оно должно быть больше 400 с каждой стороны")
                return False
            basename = os.path.basename(image_path).lower()
            if any(x in basename for x in ['icon', 'preview', 'thumb']):
                return False
            return True
        except Exception:
            return False

    def closeEvent(self, event):
        if hasattr(self, 'ocr_thread') and self.ocr_thread is not None:
            self.ocr_thread.quit()
            self.ocr_thread.wait()
        if hasattr(self, 'batch_thread') and self.batch_thread is not None:
            self.batch_thread.quit()
            self.batch_thread.wait()
        super().closeEvent(event)

    def clear_ocr_cache(self):
        self.ocr_cache.clear()
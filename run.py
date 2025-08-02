import os
import sys
import cv2
import re
import numpy as np
import hashlib
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QPushButton, QToolButton, QMenu, QAction,
                             QFileDialog, QListWidget, QListWidgetItem, QHBoxLayout, QMessageBox, QProgressBar,
                             QFrame, QScrollArea, QToolTip, QGroupBox, QSlider, QGraphicsOpacityEffect, QTextEdit,
                             QScroller, QAbstractItemView, QStyle, QSizePolicy, QInputDialog, QComboBox)
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor, QImage, QCursor, QFont, QIcon, QRegion, QPainterPath, QTextCursor
from PyQt5.QtCore import (Qt, QRect, QPoint, QSize, QTimer, QRectF, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup, QUrl, QThread,
                          pyqtSignal, QByteArray, QBuffer, pyqtSlot)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from manga_ocr import MangaOcr
from PIL import Image
from io import BytesIO
from loguru import logger
import time
import torch
import warnings
from collections import OrderedDict
from ultralytics import YOLO
__version__ = "0.9.0-open-beta"

warnings.filterwarnings("ignore", category=UserWarning, module="torchvision")
warnings.filterwarnings("ignore", category=UserWarning, module="torch.nn.modules.module")
logger.remove()

def resource_path(relative_path):
    if hasattr(sys, '_internal'):
        return os.path.join(sys._internal, relative_path)
    return os.path.join(os.path.dirname(__file__), relative_path)

ocr_path = resource_path('model_manga_ocr')

def natural_key(string):
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r'(\d+)', string)]

def pixmap_md5(pixmap):
    ba = QByteArray()
    buffer = QBuffer(ba)
    buffer.open(QBuffer.WriteOnly)
    pixmap.save(buffer, "PNG")
    md5 = hashlib.md5(bytes(ba)).hexdigest()
    return md5

class ModelLoadThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, load_func, parent=None):
        super().__init__(parent)
        self.load_func = load_func

    def run(self):
        try:
            model = self.load_func()
            self.finished.emit(model)
        except Exception as e:
            self.error.emit(str(e))

class OCRThread(QThread):
    finished = pyqtSignal(list, object, object) 
    progress = pyqtSignal(int, int, object)

    def __init__(self, app_ref, image_item):
        super().__init__()
        self.app_ref = app_ref
        self.image_item = image_item

    def run(self):
        if self.image_item.path:
            img_cv = self.app_ref.imread_unicode(self.image_item.path)
        elif self.image_item.pixmap:
            qimg = self.image_item.pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
            width, height = qimg.width(), qimg.height()
            ptr = qimg.bits()
            ptr.setsize(qimg.byteCount())
            bytes_per_line = qimg.bytesPerLine()
            arr = np.frombuffer(ptr, np.uint8).reshape((height, bytes_per_line))
            arr = arr[:, :width*3].reshape((height, width, 3))
            img_cv = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        else:
            self.finished.emit(text_boxes, img_cv, getattr(self, 'token', None))
            return

        boxes = self.app_ref.detect_text_boxes(img_cv)
        total = len(boxes)
        text_boxes = []
        h_img, w_img = img_cv.shape[:2]
        for idx, box in enumerate(boxes):
            x, y, w, h = cv2.boundingRect(box)
            x = max(0, x)
            y = max(0, y)
            w = min(w, w_img - x)
            h = min(h, h_img - y)
            self.progress.emit(idx + 1, total, getattr(self, 'token', None))
            if w <= 0 or h <= 0:
                continue
            crop_img = img_cv[y:y+h, x:x+w]
            if crop_img is None or crop_img.size == 0:
                continue
            try:
                pil_img = Image.fromarray(cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB))
            except Exception:
                continue
            text = self.app_ref.mocr(pil_img) if self.app_ref.mocr else ""
            rect = QRect(x, y, w, h)
            text_boxes.append(MangaTextBox(rect, text))
            self.progress.emit(idx + 1, total, getattr(self, 'token', None))

        self.finished.emit(text_boxes, img_cv, getattr(self, 'token', None))

class MangaDownloadThread(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)
    image_ready = pyqtSignal(QPixmap, str)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            import requests
            from bs4 import BeautifulSoup
            from PyQt5.QtGui import QPixmap
            import numpy as np
            import cv2

            response = requests.get(self.url)
            soup = BeautifulSoup(response.text, "html.parser")
            img_tags = soup.find_all("img")
            count = 0
            for img in img_tags:
                img_url = img.get("src") or img.get("data-src")
                if not img_url:
                    continue
                try:
                    img_data = requests.get(img_url).content
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_data)
                    if pixmap.isNull() or pixmap.width() < 400 or pixmap.height() < 400:
                        continue
                    arr = np.frombuffer(img_data, np.uint8)
                    img_cv = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                    if img_cv is None or img_cv.shape[0] < 400 or img_cv.shape[1] < 400:
                        continue
                    self.image_ready.emit(pixmap, f"{count+1:03}.jpg")
                    count += 1
                    self.progress.emit(count)
                except Exception as e:
                    print(f"Ошибка загрузки {img_url}: {e}")
            self.finished.emit(count)
        except Exception as e:
            self.error.emit(str(e))

class SmoothListWidget(QListWidget):
    def wheelEvent(self, event):
        scroll_bar = self.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.value() - event.angleDelta().y() // 8)

class MangaTextBox:
    def __init__(self, rect, text):
        self.rect = rect
        self.text = text

class ImageItem:
    def __init__(self, pixmap=None, path=None, name=None):
        self.pixmap = pixmap
        self.path = path
        self.name = name

class ImagePreviewItem(QListWidgetItem):
    def __init__(self, image_path, thumb_size=(120, 160)):
        super().__init__()
        self.image_path = image_path
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.setText(os.path.basename(image_path))
        else:
            icon = QIcon(pixmap.scaled(*thumb_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.setIcon(icon)
            self.setText(os.path.basename(image_path))

class TitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.setFixedHeight(40)

        self.title_label = QLabel("MangaOCR App")
        self.title_label.setStyleSheet("""
            font-weight: 700;
            font-size: 16px;
            color: #f0f0f0;
            padding-left: 10px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: transparent;
        """)

        self.btn_minimize = QPushButton("—")
        self.btn_close = QPushButton("✕")

        for btn in (self.btn_minimize, self.btn_close):
            btn.setFixedSize(40, 28)

        self.btn_minimize.clicked.connect(self.on_minimize)
        self.btn_close.clicked.connect(self.on_close)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_close)

        self._start_pos = None

    def paintEvent(self, event):
        pass

    def on_minimize(self):
        self.parent.showMinimized()

    def on_close(self):
        self.parent.close()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self._start_pos:
            delta = event.globalPos() - self._start_pos
            self.parent.move(self.parent.pos() + delta)
            self._start_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self._start_pos = None

class BatchOCRThread(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)

    def __init__(self, app_ref, image_list):
        super().__init__()
        self.app_ref = app_ref
        self.image_list = image_list

    def run(self):
        results = []
        total = len(self.image_list)
        cache = self.app_ref.ocr_cache  # Используем кэш приложения
        for idx, image_item in enumerate(self.image_list):
            # --- Ключ для кэша ---
            if image_item.path:
                cache_key = image_item.path
            elif image_item.pixmap:
                cache_key = pixmap_md5(image_item.pixmap)
            else:
                continue

            # --- Проверка кэша ---
            if cache_key in cache:
                text_boxes, img_cv = cache[cache_key]
            else:
                # --- Загрузка изображения ---
                if image_item.path:
                    img_cv = self.app_ref.imread_unicode(image_item.path)
                elif image_item.pixmap:
                    qimg = image_item.pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
                    width, height = qimg.width(), qimg.height()
                    ptr = qimg.bits()
                    ptr.setsize(qimg.byteCount())
                    bytes_per_line = qimg.bytesPerLine()
                    arr = np.frombuffer(ptr, np.uint8).reshape((height, bytes_per_line))
                    arr = arr[:, :width*3].reshape((height, width, 3))
                    img_cv = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                else:
                    continue

                boxes = self.app_ref.detect_text_boxes(img_cv)
                text_boxes = self.app_ref.group_and_recognize_lines(img_cv, boxes)
                cache[cache_key] = (text_boxes, img_cv)  # --- Сохраняем в кэш ---

            results.append((image_item, text_boxes))
            self.progress.emit(idx + 1, total)
        self.finished.emit(results)

class TextExportPanel(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.all_text_lines = []  # Сохраняем все строки всех страниц
        self.page_indices = []    # Индексы начала каждой страницы в all_text_lines
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Текстовое поле
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Здесь появится результат пакетной обработки…")
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background: #121212;
                color: #e0e0e0;
                border-radius: 10px;
                border: 1px solid #444;
                font-size: 14px;
                padding: 8px;
                min-height: 120px;
                font-family: "Segoe UI", "Yu Gothic";
            }
            QScrollBar:vertical {
                border: none;
                background: #2e2e2e;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #888888;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        layout.addWidget(self.text_edit)

        self.text_edit.verticalScrollBar().valueChanged.connect(self._update_arrow_positions)
        self.parent_app.image_list_widget.currentRowChanged.connect(self.show_selected_page_text)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_process = QPushButton("Обработать")
        self.btn_process.setStyleSheet("""
            QPushButton {
                background-color: #3a7afe;
                color: #fff;
                border: none;
                border-radius: 8px;
                padding: 7px 18px;
                font-weight: 500;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5591ff;
            }
        """)

        self.btn_export = QPushButton("Сохранить как…")
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #23242a;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 7px 18px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #3a7afe;
                color: #fff;
            }
        """)

        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_process)
        btn_layout.addWidget(self.btn_export)
        layout.addLayout(btn_layout)

        self.btn_process.clicked.connect(self.process_all)
        self.btn_export.clicked.connect(self.export_text)

    def get_frame_rects(self, img_cv):
        frame_rects = []
        if self.parent_app.yolo_detector is not None:
            results = self.parent_app.yolo_detector(img_cv, iou=0.05)
            for r in results[0].boxes:
                if int(r.cls[0]) == 2:
                    x1, y1, x2, y2 = map(int, r.xyxy[0].cpu().numpy())
                    frame_rects.append(QRect(x1, y1, x2 - x1, y2 - y1))
        return frame_rects

    def process_all(self):
        self.parent_app.notification("Обработка...")
        self.parent_app.ocr_progress.setVisible(True)
        self.parent_app.ocr_progress.setValue(0)
        self.parent_app.ocr_progress.setMaximum(len(self.parent_app.image_list))

        def on_progress(current, total):
            self.parent_app.ocr_progress.setMaximum(total)
            self.parent_app.ocr_progress.setValue(current)

        def on_finished(results):
            self.parent_app.ocr_progress.setVisible(False)
            self.parent_app.all_text_boxes = results
            self.all_text_lines = []
            self.page_indices = []
            self.line_to_box_idx = []
            for idx, (image_item, boxes) in enumerate(results):
                self.page_indices.append(len(self.all_text_lines))
                filename = ""
                if image_item.path:
                    filename = os.path.splitext(os.path.basename(image_item.path))[0]
                elif image_item.name:
                    filename = os.path.splitext(os.path.basename(image_item.name))[0]
                else:
                    filename = f"{idx+1}"
                self.all_text_lines.append(filename)
                self.line_to_box_idx.append(None)
                # Загружаем изображение
                if image_item.path:
                    img_cv = self.parent_app.imread_unicode(image_item.path)
                elif image_item.pixmap:
                    qimg = image_item.pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
                    width, height = qimg.width(), qimg.height()
                    ptr = qimg.bits()
                    ptr.setsize(qimg.byteCount())
                    bytes_per_line = qimg.bytesPerLine()
                    arr = np.frombuffer(ptr, np.uint8).reshape((height, bytes_per_line))
                    arr = arr[:, :width*3].reshape((height, width, 3))
                    img_cv = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                else:
                    continue

                frame_rects = self.get_frame_rects(img_cv)
                frame_dict = { (f.left(), f.top(), f.width(), f.height()): {'rect': f, 'boxes': []} for f in frame_rects }
                unframed = []
                for box in boxes:
                    assigned = False
                    main_frame = get_box_main_frame(box, frame_rects)
                    if main_frame is not None:
                        key = (main_frame.left(), main_frame.top(), main_frame.width(), main_frame.height())
                        frame_dict[key]['boxes'].append(box)
                        assigned = True
                    else:
                        assigned = False
                    if not assigned:
                        unframed.append(box)

                def sort_frames_manga_style(frames, overlap_threshold=5):
                    """
                    Улучшенная сортировка фреймов по стилю манги:
                    - Сначала группирует фреймы в строки по вертикальному перекрытию (top/bottom)
                    - Затем сортирует строки сверху вниз
                    - Внутри строки сортирует справа налево
                    """
                    def is_same_row(f, row):
                        for r in row:
                            top1, bottom1 = f[1], f[1] + f[3]
                            top2, bottom2 = r[1], r[1] + r[3]
                            overlap = min(bottom1, bottom2) - max(top1, top2)
                            if overlap >= -overlap_threshold:
                                return True
                        return False

                    # Сначала сортируем по top (сверху вниз)
                    frames = sorted(frames, key=lambda f: f[1])

                    rows = []
                    for f in frames:
                        placed = False
                        for row in rows:
                            if is_same_row(f, row):
                                row.append(f)
                                placed = True
                                break
                        if not placed:
                            rows.append([f])

                    # Сортируем строки сверху вниз
                    rows.sort(key=lambda row: min(f[1] for f in row))

                    # В каждой строке сортируем справа налево
                    sorted_result = []
                    for row in rows:
                        row_sorted = sorted(row, key=lambda f: -f[0])
                        sorted_result.extend(row_sorted)

                    return sorted_result

                frame_keys = list(frame_dict.keys())
                sorted_keys = sort_frames_manga_style(frame_keys, overlap_threshold=5)
                for key in sorted_keys:
                    for tbox in sort_boxes_with_tolerance(frame_dict[key]['boxes']):
                        self.all_text_lines.append(tbox.text.strip())
                        try:
                            real_box_idx = boxes.index(tbox)
                        except ValueError:
                            real_box_idx = None
                        self.line_to_box_idx.append((idx, real_box_idx))

                if unframed:
                    self.all_text_lines.append("[Вне фреймов]")
                    self.line_to_box_idx.append(None)
                    for tbox in sorted(unframed, key=lambda b: (-b.rect.left(), b.rect.top())):
                        self.all_text_lines.append(tbox.text.strip())
                        try:
                            real_box_idx = boxes.index(tbox)
                        except ValueError:
                            real_box_idx = None
                        self.line_to_box_idx.append((idx, real_box_idx))
        
        if self.parent_app.image_list_widget.count() > 0:
            self.parent_app.image_list_widget.setCurrentRow(0)
            self.show_selected_page_text(0)

        if hasattr(self, 'batch_thread') and self.batch_thread is not None:
            self.batch_thread.quit()
            self.batch_thread.wait()
        self.batch_thread = BatchOCRThread(self.parent_app, self.parent_app.image_list)
        self.batch_thread.progress.connect(on_progress)
        self.batch_thread.finished.connect(on_finished)
        self.batch_thread.start()

        def get_box_main_frame(box, frame_rects):
            max_inter = 0
            main_frame = None
            box_rect = box.rect
            for f in frame_rects:
                inter = box_rect.intersected(f)
                area = inter.width() * inter.height()
                if area > max_inter:
                    max_inter = area
                    main_frame = f
            return main_frame
        
        def sort_boxes_with_tolerance(boxes, x_tolerance=20):
            def box_key(b):
                return (round(-b.rect.left() / x_tolerance), b.rect.top())
            return sorted(boxes, key=box_key)

    def show_selected_page_text(self, page_idx):
        if not self.all_text_lines or page_idx < 0 or page_idx >= len(self.page_indices):
            self.text_edit.clear()
            return
        start = self.page_indices[page_idx]
        end = self.page_indices[page_idx + 1] if page_idx + 1 < len(self.page_indices) else len(self.all_text_lines)
        page_lines = self.all_text_lines[start:end]
        self.set_zebra_text(page_lines)

    def set_zebra_text(self, lines):
        if not lines:
            self.text_edit.clear()
            return

        html_lines = []
        zebra_idx = 0

        for i, line in enumerate(lines):
            if i == 0:
                html_lines.append(
                    '<div style="background:#252525; color:#fff; border:1.5px solid #444; border-radius:10px;'
                    'padding:6px 12px; margin:10px 0 6px 0; font-weight:bold; font-size:15px; letter-spacing:0.5px;'
                    'user-select:none; pointer-events:none;" contenteditable="false">'
                    f'{line}'
                    '</div>'
                )
                zebra_idx = 0
            else:
                bg = "#444444" if zebra_idx % 2 == 0 else "#121212"
                html_lines.append(
                    f'<div style="background:{bg}; border-radius:7px; padding:4px 10px; margin-bottom:2px;">'
                    f'{line}'
                    '</div>'
                )
                zebra_idx += 1

        html = (
            "<div style='font-family:\"Yu Gothic UI\",\"Yu Gothic\",\"Meiryo\",\"Segoe UI\",sans-serif;"
            "font-size:14px;color:#e0e0e0;padding:4px 0;background:transparent;'>"
            + "".join(html_lines)
            + "</div>"
        )
        self.text_edit.setHtml(html)
        self._add_arrows(len(lines))

    def _update_arrow_positions(self):
        scrollbar_width = self.text_edit.verticalScrollBar().width()
        page_idx = self.parent_app.image_list_widget.currentRow()
        if page_idx < 0 or page_idx >= len(self.page_indices):
            return
        start = self.page_indices[page_idx]
        end = self.page_indices[page_idx + 1] if page_idx + 1 < len(self.page_indices) else len(self.all_text_lines)
        arrow_btn_idx = 0
        for i in range(1, end - start):
            global_idx = start + i
            if self.line_to_box_idx[global_idx] is None:
                continue
            if arrow_btn_idx >= len(self._arrow_buttons):
                break  # Нет больше кнопок для позиционирования
            cursor = QTextCursor(self.text_edit.document().findBlockByLineNumber(i))
            rect = self.text_edit.cursorRect(cursor)
            btn = self._arrow_buttons[arrow_btn_idx]
            btn.move(self.text_edit.width() - 32 - scrollbar_width, rect.top())
            arrow_btn_idx += 1

    def _clear_arrows(self):
        if hasattr(self, '_arrow_buttons'):
            for btn in self._arrow_buttons:
                btn.deleteLater()
        self._arrow_buttons = []

    def _add_arrows(self, line_count):
        self._clear_arrows()
        self._arrow_buttons = []
        # Получаем диапазон строк для текущей страницы
        page_idx = self.parent_app.image_list_widget.currentRow()
        if page_idx < 0 or page_idx >= len(self.page_indices):
            return
        start = self.page_indices[page_idx]
        end = self.page_indices[page_idx + 1] if page_idx + 1 < len(self.page_indices) else len(self.all_text_lines)
        # Для строк текущей страницы (но пропускаем первую строку — заголовок)
        for i in range(1, end - start):  # начинаем с 1, чтобы пропустить заголовок
            global_idx = start + i
            if self.line_to_box_idx[global_idx] is None:
                continue
            btn = QPushButton(">", self.text_edit)
            btn.setFixedSize(28, 24)
            btn.setStyleSheet("""
                QPushButton {
                    color: #3a7afe;
                    border: none;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 0 4px;
                }
                QPushButton:hover {
                    color: #fff;
                }
            """)
            cursor = QTextCursor(self.text_edit.document().findBlockByLineNumber(i))
            rect = self.text_edit.cursorRect(cursor)
            scrollbar_width = self.text_edit.verticalScrollBar().width()
            btn.move(self.text_edit.width() - 32 - scrollbar_width, rect.top())
            btn.clicked.connect(lambda _, idx=global_idx: self._on_arrow(idx))
            btn.show()
            self._arrow_buttons.append(btn)
        self._update_arrow_positions()

    def _on_arrow(self, idx):
        box_info = self.line_to_box_idx[idx]
        if box_info is not None:
            image_idx, local_box_idx = box_info
            # Если выбранная картинка не совпадает — переключаемся
            if self.parent_app.image_list_widget.currentRow() != image_idx:
                self.parent_app.image_list_widget.setCurrentRow(image_idx)
                self.parent_app.load_selected_image(self.parent_app.image_list_widget.item(image_idx))
            # После этого text_boxes обновится, и можно подсветить нужный бокс
            QTimer.singleShot(100, lambda: self.parent_app.highlight_box_by_line(local_box_idx))

    def export_text(self):
        text = "\n".join(self.all_text_lines)  # Экспортируем весь текст, а не только текущую страницу
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить текст", "", "Текстовый файл (*.txt);;Документ Word (*.docx)")
        if path:
            if path.endswith(".docx"):
                try:
                    from docx import Document
                    doc = Document()
                    for line in self.all_text_lines:
                        doc.add_paragraph(line)
                    doc.save(path)
                except ImportError:
                    QMessageBox.warning(self, "Ошибка", "Для экспорта в docx установите python-docx")
            else:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(text)

class MangaOCRApp(QWidget):
    def __init__(self):
        super().__init__()

        self.mocr = None
        self.ocr_cache = {}
        self.all_text_boxes = []
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.start_mangaocr_load()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("MainWindowBg")
        self.setStyleSheet("""
            QWidget#MainWindowBg {
                background-color: #121212;
                border-radius: 20px;
                border: 1px solid #222;
            }
        """)

        dark_stylesheet = """
            QWidget {
                background-color: #121212;
                color: #e0e0e0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                font-size: 14px;
            }
            QPushButton {
                background-color: #1f1f1f;
                border: 1px solid #444;
                padding: 6px;
                border-radius: 10px;
                outline: none;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 0;
                border-radius: 10px;
                outline: none;
            }
            QPushButton:focus {
                background-color: #1f1f1f;
                border: 1px solid #444;
                outline: none;
            }
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #444;
                border-radius: 10px;
                outline: none;
            }
            QListWidget::item:selected {
                background-color: #3a3a3a;
                color: #ffffff;
                border: 0;
                border-radius: 7px;
                outline: none;
            }
            QLabel {
                background-color: #121212;
            }
            QMessageBox {
                background-color: #121212;
                color: #e0e0e0;
            }
        """
        self.setStyleSheet(dark_stylesheet)

        self.setWindowTitle("MangaOCR App")
        self.setWindowFlags(Qt.FramelessWindowHint)
        screen = QApplication.primaryScreen()
        rect = screen.availableGeometry()

        width = int(rect.width() * 0.8)
        height = int(rect.height() * 0.8)

        self.setGeometry(100, 100, width, height)

        self.setMinimumSize(int(width * 0.6), int(height * 0.6))

        self.setAcceptDrops(True)

        self.image_list = []
        self.current_image_path = None
        self.text_boxes = []
        self.history = []

        self.init_ui()

    def load_mangaocr_model(self):
        from manga_ocr import MangaOcr
        return MangaOcr(pretrained_model_name_or_path=ocr_path)

    def start_mangaocr_load(self):
        self.mangaocr_thread = ModelLoadThread(self.load_mangaocr_model)
        self.mangaocr_thread.finished.connect(self.on_mangaocr_loaded)
        self.mangaocr_thread.error.connect(lambda msg: self.notification(f"Ошибка загрузки MangaOCR: {msg}"))
        self.mangaocr_thread.start()

    def on_mangaocr_loaded(self, model):
        self.mocr = model
        self.auto_load_images()
    
    def auto_load_images(self):
        input_dir = os.path.join(os.path.dirname(__file__), "input")
        if os.path.isdir(input_dir):
            self.image_list = [
                ImageItem(path=os.path.join(input_dir, f))
                for f in sorted(os.listdir(input_dir), key=natural_key)
                if f.lower().endswith(('.jpg', '.png', '.jpeg')) and
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

    def create_settings_panel(self):
        settings_group = QWidget()

        layout = QVBoxLayout(settings_group)

        self.slider_max_vertical_gap = self.create_slider("Макс. вертикальный зазор", 50, 300, 100,
            "Максимальный вертикальный интервал между блоками текста (в процентах от средней высоты). Больше - сильнее соединяет.")

        self.slider_max_horizontal_gap = self.create_slider("Макс. горизонтальный зазор", 50, 300, 120,
            "Максимальный горизонтальный интервал между блоками текста (в процентах от средней ширины). Больше - сильнее соединяет.")

        self.slider_vertical_shift_ratio = self.create_slider("Допустимый вертикальный сдвиг", 0, 100, 50,
            "Относительное смещение по вертикали, при котором блоки считаются на одной строке. Больше - сильнее соединяет.")

        self.slider_merge_tolerance = self.create_slider("Толерантность объединения", 0, 100, 0,
            "Расстояние (в процентах), при котором пересекающиеся боксы соединяются. Меньше - сильнее соединяет.")

        self.slider_min_bubble_gap = self.create_slider(
            "Мин. зазор между баблами", 0, 100, 20,
            "Минимальное расстояние (в пикселях) между группами, при котором они не будут объединяться. Больше - сильнее соединяет."
        )

        self.slider_max_vertical_gap['slider'].sliderReleased.connect(self.on_slider_released)
        self.slider_max_horizontal_gap['slider'].sliderReleased.connect(self.on_slider_released)
        self.slider_vertical_shift_ratio['slider'].sliderReleased.connect(self.on_slider_released)
        self.slider_merge_tolerance['slider'].sliderReleased.connect(self.on_slider_released)
        self.slider_min_bubble_gap['slider'].sliderReleased.connect(self.on_slider_released)

        layout.addWidget(self.slider_max_vertical_gap['container'])
        layout.addWidget(self.slider_max_horizontal_gap['container'])
        layout.addWidget(self.slider_vertical_shift_ratio['container'])
        layout.addWidget(self.slider_merge_tolerance['container'])
        layout.addWidget(self.slider_min_bubble_gap['container'])

        settings_group.setLayout(layout)
        return settings_group

    def on_slider_released(self):
        if hasattr(self, 'current_image_path') and self.current_image_path:
            self.process_image()

    def create_slider(self, label_text, min_val, max_val, default_val, tooltip):
        container = QWidget()
        layout = QVBoxLayout()
        container.setLayout(layout)

        label = QLabel(f"{label_text}: {default_val}")
        label.setToolTip(tooltip)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(default_val)
        slider.valueChanged.connect(lambda val: label.setText(f"{label_text}: {val}"))
        slider.setToolTip(tooltip)

        layout.addWidget(label)
        layout.addWidget(slider)
        return {"container": container, "label": label, "slider": slider}
    
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
        self.btn_select_folder.setStyleSheet("""
            QPushButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #00bfff;
            }
        """)

        self.btn_paste_clipboard = QPushButton()
        self.btn_paste_clipboard.setIcon(QIcon("icons/clipboard.svg"))
        self.btn_paste_clipboard.setToolTip("Вставить изображение из буфера обмена")
        self.btn_paste_clipboard.setMinimumHeight(38)
        self.btn_paste_clipboard.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_paste_clipboard.clicked.connect(self.paste_from_clipboard)
        self.btn_paste_clipboard.setStyleSheet("""
            QPushButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #00bfff;
            }
        """)

        self.btn_yolo_model = QToolButton()
        self.btn_yolo_model.setText("M")
        self.btn_yolo_model.setToolTip("Выбрать YOLO модель")
        self.btn_yolo_model.setMinimumHeight(38)
        self.btn_yolo_model.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_yolo_model.setPopupMode(QToolButton.InstantPopup)
        self.btn_yolo_model.setStyleSheet("""
            QToolButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
                color: #e0e0e0;
                font-size: 15px;
                padding: 0 18px;
            }
            QToolButton::menu-indicator {
                image: none;
                width: 0px;
            }
            QMenu {
                background-color: #23242a;
                color: #e0e0e0;
                border-radius: 8px;
                font-size: 15px;
            }
            QMenu::item:selected {
                background-color: #2e2f36;
                border: 1px solid #3a7afe;
            }
        """)

        self.yolo_menu = QMenu()
        self.yolo_menu.setStyleSheet("""
            QMenu {
                background-color: #23242a;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 10px;
                padding: 6px 0;
                font-size: 15px;
                font-family: 'Segoe UI', 'Yu Gothic', Arial, sans-serif;
            }
            QMenu::item {
                background: transparent;
                padding: 8px 24px 8px 24px;
                border-radius: 8px;
                margin: 2px 8px;
            }
            QMenu::item:selected {
                background-color: #3a7afe;
                color: #fff;
            }
            QMenu::separator {
                height: 1px;
                background: #444;
                margin: 4px 8px;
            }
        """)
        self.yolo_models = {
            "N": "yoloModels/yolo_n.pt",
            "S": "yoloModels/yolo_s.pt",
            "M": "yoloModels/yolo_m.pt",
            "L": "yoloModels/yolo_l.pt",
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
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #ff5555;
            }
        """)

        self.btn_jardic = QPushButton()
        self.btn_jardic.setIcon(QIcon("icons/jardic.png")) 
        self.btn_jardic.setToolTip("Открыть Jardic")
        self.btn_jardic.setMinimumHeight(38)
        self.btn_jardic.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_jardic.clicked.connect(self.toggle_jardic_browser)
        self.btn_jardic.setStyleSheet("""
            QPushButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #3a7afe;
            }
        """)

        folder_clipboard_row.addWidget(self.btn_select_folder)
        folder_clipboard_row.addWidget(self.btn_clear)
        folder_clipboard_row.addWidget(self.btn_yolo_model)
        folder_clipboard_row.addWidget(self.btn_paste_clipboard)
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
        self.image_list_widget.verticalScrollBar().setStyleSheet("""
            QScrollBar:vertical {
                border: none;
                background: #2e2e2e;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #888888;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)

        left_panel.addWidget(self.image_list_widget)

        self.toggle_panel_buttons_layout = QHBoxLayout()
        self.btn_toggle_settings = QPushButton("О программе ▲")
        self.btn_toggle_group = QPushButton("Текст ▲")

        for btn in (self.btn_toggle_settings, self.btn_toggle_group):
            btn.setFixedHeight(30)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #e0e0e0;
                    font-weight: bold;
                    padding: 5px;
                    text-align: center;
                }
                QPushButton:hover {
                    color: #ffffff;
                }
            """)
        self.toggle_panel_buttons_layout.addWidget(self.btn_toggle_settings)
        self.toggle_panel_buttons_layout.addWidget(self.btn_toggle_group)

        self.settings_group_panel = QGroupBox()
        self.settings_group_panel.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 10px;
                margin-top: 6px;
            }
        """)
        self.settings_group_panel.setMaximumHeight(0)  
        self.settings_group_panel.setTitle("")
        self.settings_group_panel_layout = QVBoxLayout()
        self.settings_group_panel.setLayout(self.settings_group_panel_layout)

        self.settings_content = QWidget()
        self.settings_content.setLayout(QVBoxLayout())

        about_label = QLabel(
            f"""<b>Устройство обработки</b>: {self.device}<br><br>
        <b>Горячие клавиши:</b><br>
        <tt>Ctrl + O</tt>: открыть папку с изображениями<br>
        <tt>Ctrl + V</tt>: вставить из буфера обмена (распознаёт папки, ссылки на главы с Rawkuma и просто изображения)<br>
        <tt>Ctrl + S</tt>: сохранить текстовый результат<br>
        <tt>Ctrl + R</tt>: очистить кэш<br>
        <tt>Ctrl + L</tt>: очистить список изображений<br>
        <tt>Ctrl + Z</tt>: отмена<br>
        <tt>J</tt>: открыть/закрыть Jardic<br><br>
        <b>Работа с изображением:</b><br>
        <tt>ЛКМ</tt>: скопировать текст в буфер обмена<br>
        <tt>ПКМ</tt>: вставить в поле Jardic<br><br>
        <b>Новости и обновления в
        <a href="https://t.me/MangaOCRApp" style="color:#3a7afe; text-decoration:underline; font-weight:bold;">телеграме</a></b><br>
        Версия: {__version__}</b><br>
        """
        )
        about_label.setWordWrap(True)
        about_label.setTextFormat(Qt.RichText)
        about_label.setOpenExternalLinks(True)
        self.settings_content.layout().addWidget(about_label)

        self.group_content = TextExportPanel(self)

        left_panel.addLayout(self.toggle_panel_buttons_layout)
        left_panel.addWidget(self.settings_group_panel)

        from PyQt5.QtCore import QPropertyAnimation, QEasingCurve
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

        self.hovered_text = QLabel(self.image_label)
        self.hovered_text.setObjectName("hovered_text")
        self.hovered_text.setStyleSheet("""
            background-color: #2e2e2e;
            color: #ffffff;
            padding: 6px 10px;
            border: 1px solid #555555;
            outline: none;
            border-radius: 10px;
            font-size: 14px;
            font-family: "Yu Gothic";
        """)
        self.hovered_text.hide()

        self.ocr_progress = QProgressBar(self)
        self.ocr_progress.setMinimum(0)
        self.ocr_progress.setMaximum(100)
        self.ocr_progress.setValue(0)
        self.ocr_progress.setAlignment(Qt.AlignCenter)
        self.ocr_progress.setVisible(False)
        self.ocr_progress.setFixedSize(220, 26)
        self.ocr_progress.setStyleSheet("""
            QProgressBar {
                background: #222;
                color: #fff;
                border-radius: 10px;
                border: 1px solid #444;
                font-size: 11px;
                padding: 1px 6px;
            }
            QProgressBar::chunk {
                background: #3a7afe;
                border-radius: 8px;
            }
        """)

        self.jardic_browser = QWebEngineView()
        self.jardic_browser.setUrl(QUrl("https://jardic.ru/"))
        self.jardic_browser.setVisible(False)
        self.jardic_browser.setMinimumWidth(400)
        self.jardic_browser.setStyleSheet("""
            border-radius: 20px;
            background: transparent;
        """)
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
            self.current_image_path
        ))
        if len(self.history) > 100:
            self.history.pop(0)

    def undo_action(self):
        if not self.history:
            self.notification("Нет действий для отмены.")
            return
        prev_list, prev_path = self.history.pop()
        self.image_list = prev_list
        self.current_image_path = prev_path
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
        if self.current_image_path and self.current_image_path in self.image_list:
            idx = self.image_list.index(self.current_image_path)
            self.image_list_widget.setCurrentRow(idx)
            self.process_image()
        else:
            self.image_label.clear()
            self.text_boxes = []

    def HideSettingsPanel(self):
        self.settings_panel.hide()
        self.settings_opacity_effect.setOpacity(0)
    
    def select_folder(self):
        input_dir = QFileDialog.getExistingDirectory(self, "Выбрать папку с изображениями")
        if input_dir:
            self.save_history()
            self.image_list = [
                ImageItem(path=os.path.join(input_dir, f))
                for f in sorted(os.listdir(input_dir), key=natural_key)
                if f.lower().endswith(('.jpg', '.png', '.jpeg')) and
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

    def process_image(self):
        image_item = None
        if self.current_image_path is not None:
            for item in self.image_list:
                if item.path == self.current_image_path:
                    image_item = item
                    break
        elif self.image_list_widget.currentRow() >= 0:
            image_item = self.image_list[self.image_list_widget.currentRow()]

        if image_item is None:
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить изображение")
            return

        if image_item.path:
            img_cv = self.imread_unicode(image_item.path)
        elif image_item.pixmap:
            qimg = image_item.pixmap.toImage().convertToFormat(QImage.Format.Format_RGB888)
            width, height = qimg.width(), qimg.height()
            ptr = qimg.bits()
            ptr.setsize(qimg.byteCount())
            bytes_per_line = qimg.bytesPerLine()
            arr = np.frombuffer(ptr, np.uint8).reshape((height, bytes_per_line))
            arr = arr[:, :width*3].reshape((height, width, 3))
            img_cv = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить изображение")
            return

        boxes = self.detect_text_boxes(img_cv)
        self.text_boxes = self.group_and_recognize_lines(img_cv, boxes)
        self.display_image_with_boxes(img_cv)

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

    def group_boxes_by_vertical_and_horizontal(self, boxes):
        if len(boxes) == 0:
            return []

        heights = [np.max(box[:,1]) - np.min(box[:,1]) for box in boxes]
        avg_height = np.mean(heights)
        max_vertical_gap = avg_height * (self.slider_max_vertical_gap['slider'].value() / 100)
        tolerance = self.slider_merge_tolerance['slider'].value() / 100
        widths = [np.max(box[:,0]) - np.min(box[:,0]) for box in boxes]
        avg_width = np.mean(widths)
        max_horizontal_gap = avg_width * (self.slider_max_horizontal_gap['slider'].value() / 100)
        max_vertical_shift_ratio = self.slider_vertical_shift_ratio['slider'].value() / 100

        ranges = []
        for i, box in enumerate(boxes):
            x_min = np.min(box[:,0])
            x_max = np.max(box[:,0])
            y_min = np.min(box[:,1])
            y_max = np.max(box[:,1])
            y_center = np.mean(box[:,1])
            ranges.append({'idx': i, 'x_min': x_min, 'x_max': x_max, 'y_min': y_min, 'y_max': y_max, 'y_center': y_center})

        ranges.sort(key=lambda r: r['y_center'])

        groups = []
        current_group = [ranges[0]['idx']]
        cur_y_center = ranges[0]['y_center']
        cur_x_max = ranges[0]['x_max']

        for r in ranges[1:]:
            y_diff = abs(r['y_center'] - cur_y_center)
            x_gap = r['x_min'] - cur_x_max
            x_overlap = cur_x_max - r['x_min']

            if y_diff <= max_vertical_gap and (0 <= x_gap <= max_horizontal_gap or x_overlap > -max_horizontal_gap * 0.3):
                current_group.append(r['idx'])
                cur_y_center = (cur_y_center * (len(current_group) - 1) + r['y_center']) / len(current_group)
                cur_x_max = max(cur_x_max, r['x_max'])
            else:

                subgroups = self.split_group_horizontally(boxes, current_group, max_horizontal_gap, max_vertical_shift_ratio)
                groups.extend(subgroups)
                current_group = [r['idx']]
                cur_y_center = r['y_center']
                cur_x_max = r['x_max']

        if current_group:
            subgroups = self.split_group_horizontally(boxes, current_group, max_horizontal_gap, max_vertical_shift_ratio)
            groups.extend(subgroups)

        return groups
    
    def split_group_horizontally(self, boxes, group, max_gap, max_vertical_shift_ratio):

        sorted_indices = sorted(group, key=lambda i: np.min(boxes[i][:,0]))
        subgroups = []
        current_subgroup = [sorted_indices[0]]
        last_box = boxes[sorted_indices[0]]

        last_y_min = np.min(last_box[:,1])
        last_y_max = np.max(last_box[:,1])
        last_height = last_y_max - last_y_min

        for idx in sorted_indices[1:]:
            box = boxes[idx]
            y_min = np.min(box[:,1])
            y_max = np.max(box[:,1])
            height = y_max - y_min

            gap = np.min(box[:,0]) - np.max(last_box[:,0])
            vertical_shift = abs(((y_min + y_max) / 2) - ((last_y_min + last_y_max) / 2))

            max_vertical_shift = max(last_height, height) * max_vertical_shift_ratio

            if gap > max_gap or vertical_shift > max_vertical_shift:
                subgroups.append(current_subgroup)
                current_subgroup = [idx]
            else:
                current_subgroup.append(idx)

            last_box = box
            last_y_min = y_min
            last_y_max = y_max
            last_height = height

        if current_subgroup:
            subgroups.append(current_subgroup)

        return subgroups
    
    def merge_nested_groups(self, groups, boxes, tolerance):
        min_bubble_gap = self.slider_min_bubble_gap['slider'].value()

        def get_bbox_for_group(group):
            all_points = np.vstack([boxes[i] for i in group])
            x, y, w, h = cv2.boundingRect(all_points)
            return x, y, w, h

        def box_area(box):
            _, _, w, h = box
            return w * h

        def intersection_area(boxA, boxB):
            xA, yA, wA, hA = boxA
            xB, yB, wB, hB = boxB

            x_left = max(xA, xB)
            y_top = max(yA, yB)
            x_right = min(xA + wA, xB + wB)
            y_bottom = min(yA + hA, yB + hB)

            if x_right < x_left or y_bottom < y_top:
                return 0

            return (x_right - x_left) * (y_bottom - y_top)

        def bbox_distance(boxA, boxB):
            xA, yA, wA, hA = boxA
            xB, yB, wB, hB = boxB
            left = xB + wB < xA
            right = xA + wA < xB
            above = yB + hB < yA
            below = yA + hA < yB

            if above:
                if left:
                    return np.hypot(xA - (xB + wB), yA - (yB + hB))
                elif right:
                    return np.hypot((xA + wA) - xB, yA - (yB + hB))
                else:
                    return yA - (yB + hB)
            elif below:
                if left:
                    return np.hypot(xA - (xB + wB), (yA + hA) - yB)
                elif right:
                    return np.hypot((xA + wA) - xB, (yA + hA) - yB)
                else:
                    return yB - (yA + hA)
            else:
                if left:
                    return xA - (xB + wB)
                elif right:
                    return xB - (xA + wA)
                else:
                    return 0 

        merged_groups = [set(g) for g in groups]
        changed = True
        while changed:
            changed = False
            new_groups = []
            used = set()
            for i in range(len(merged_groups)):
                if i in used:
                    continue
                group_a = merged_groups[i]
                bbox_a = get_bbox_for_group(group_a)
                merged = group_a.copy()
                for j in range(i + 1, len(merged_groups)):
                    if j in used:
                        continue
                    group_b = merged_groups[j]
                    bbox_b = get_bbox_for_group(group_b)
                    inter_area = intersection_area(bbox_a, bbox_b)
                    area_a = box_area(bbox_a)
                    area_b = box_area(bbox_b)
                    overlap_a_in_b = inter_area / area_a if area_a else 0
                    overlap_b_in_a = inter_area / area_b if area_b else 0
                    dist = bbox_distance(bbox_a, bbox_b)

                    if tolerance > 0:
                        if overlap_a_in_b >= tolerance or overlap_b_in_a >= tolerance or dist <= min_bubble_gap:
                            merged.update(group_b)
                            used.add(j)
                            changed = True
                    else:
                        if dist <= min_bubble_gap:
                            merged.update(group_b)
                            used.add(j)
                            changed = True
                new_groups.append(merged)
            merged_groups = new_groups
        return [sorted(list(g)) for g in merged_groups]
    
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
        # idx — локальный индекс бокса для текущей картинки
        if 0 <= idx < len(self.text_boxes):
            self.highlighted_box_idx = idx
            self.display_image_with_boxes_highlight(idx)

    def display_image_with_boxes_highlight(self, highlight_idx):
        # Копия display_image_with_boxes, но с выделением нужного бокса
        img_cv = None
        if self.current_image_path:
            img_cv = cv2.imread(self.current_image_path)
        elif self.image_label.pixmap():
            qimg = self.image_label.pixmap().toImage().convertToFormat(QImage.Format.Format_RGB888)
            width, height = qimg.width(), qimg.height()
            ptr = qimg.bits()
            ptr.setsize(qimg.byteCount())
            bytes_per_line = qimg.bytesPerLine()
            arr = np.frombuffer(ptr, np.uint8).reshape((height, bytes_per_line))
            arr = arr[:, :width*3].reshape((height, width, 3))
            img_cv = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
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

        for i, box in enumerate(self.text_boxes):
            if i == highlight_idx:
                pen = QPen(QColor(255, 80, 80, 220), 5)  # Красная рамка
                painter.setPen(pen)
                painter.setBrush(QColor(255, 80, 80, 40))
            else:
                pen = QPen(QColor(0, 160, 230, 180), 3)
                painter.setPen(pen)
                painter.setBrush(QColor(0, 160, 230, 40))
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
            
    def display_image_with_boxes(self, image_cv):
        height, width, channel = image_cv.shape
        bytes_per_line = 3 * width
        qimage = QImage(image_cv.data, width, height, bytes_per_line, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(qimage)

        self.last_pixmap_for_cache = pixmap
        pixmap_with_boxes = QPixmap(pixmap)
        painter = QPainter(pixmap_with_boxes)
        pen = QPen(QColor(0, 160, 230, 180))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 160, 230, 40))
        font = QFont('Segoe UI', 10)
        painter.setFont(font)

        for box in self.text_boxes:
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

    def on_yolo_model_changed(self, index):
        self.yolo_model_path = self.yolo_model_selector.itemData(index)

    def load_selected_yolo_model(self):
        from ultralytics import YOLO
        self.yolo_detector = YOLO(self.yolo_model_path)
        self.notification(f"YOLO модель загружена: {self.yolo_model_path}")

    def on_mouse_move(self, event):
        pos = event.pos()

        if not hasattr(self, 'scale_x') or not hasattr(self, 'scale_y') or self.scale_x == 0 or self.scale_y == 0:
            self.hovered_text.hide()
            return

        label_size = self.image_label.size()
        pixmap = self.image_label.pixmap()
        if pixmap is None:
            self.hovered_text.hide()
            return
        pixmap_size = pixmap.size()

        offset_x = (label_size.width() - pixmap_size.width()) // 2
        offset_y = (label_size.height() - pixmap_size.height()) // 2

        x_in_pixmap = pos.x() - offset_x
        y_in_pixmap = pos.y() - offset_y

        if x_in_pixmap < 0 or y_in_pixmap < 0 or x_in_pixmap > pixmap_size.width() or y_in_pixmap > pixmap_size.height():
            self.hovered_text.hide()
            return

        orig_x = x_in_pixmap / self.scale_x
        orig_y = y_in_pixmap / self.scale_y
        orig_pos = QPoint(int(orig_x), int(orig_y))

        for box in self.text_boxes:
            if box.rect.contains(orig_pos):
                # --- Ограничение ширины по Jardic ---
                if self.jardic_browser.isVisible():
                    image_label_global = self.image_label.mapToGlobal(QPoint(0, 0))
                    jardic_global = self.jardic_browser.mapToGlobal(QPoint(0, 0))
                    max_width = jardic_global.x() - image_label_global.x() - 30  # 30px отступ
                    max_width = max(120, max_width)
                    self.hovered_text.setWordWrap(True)
                    self.hovered_text.setMaximumWidth(max_width)
                else:
                    self.hovered_text.setWordWrap(False)
                    self.hovered_text.setMaximumWidth(16777215)

                self.hovered_text.setText(box.text)
                self.hovered_text.adjustSize()

                x = pos.x() + 15
                y = pos.y() + 15

                # --- Не даём подсказке вылезать за правую границу Jardic ---
                if self.jardic_browser.isVisible():
                    image_label_global = self.image_label.mapToGlobal(QPoint(0, 0))
                    jardic_global = self.jardic_browser.mapToGlobal(QPoint(0, 0))
                    jardic_left_x = jardic_global.x() - image_label_global.x()
                    if x + self.hovered_text.width() > jardic_left_x - 10:
                        x = jardic_left_x - self.hovered_text.width() - 10
                        x = max(x, 0)

                self.hovered_text.move(x, y)
                self.hovered_text.show()
                return

        self.hovered_text.hide()

    def notification(self, message):
        if not hasattr(self, 'copy_notification'):
            self.copy_notification = QLabel(self)
            self.copy_notification.setStyleSheet("""
                background-color: #1e1e1e;
                color: white;
                padding: 8px 15px;
                border-radius: 10px;
                font-size: 15px;
                border: 1px solid #444;
            """)
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
        if event.button() == Qt.RightButton:
            pos = event.pos()
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

        pos = event.pos()

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
                qimg = self.image_label.pixmap().toImage().convertToFormat(QImage.Format.Format_RGB888)
                width, height = qimg.width(), qimg.height()
                ptr = qimg.bits()
                ptr.setsize(qimg.byteCount())
                bytes_per_line = qimg.bytesPerLine()
                arr = np.frombuffer(ptr, np.uint8).reshape((height, bytes_per_line))
                arr = arr[:, :width*3].reshape((height, width, 3))
                img_cv = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
            if img_cv is not None:
                self.display_image_with_boxes(img_cv)
        super().resizeEvent(event)
        if hasattr(self, 'ocr_progress') and hasattr(self, 'image_label'):
            label_pos = self.image_label.mapTo(self.ocr_progress.parentWidget(), QPoint(0, 0))
            x = label_pos.x() + (self.image_label.width() - self.ocr_progress.width()) // 2
            y = label_pos.y() + self.image_label.height() + 16
            self.ocr_progress.move(x, y)
    
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

    def paste_from_clipboard(self):
        self.save_history()
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()

        if mime.hasImage():
            pixmap = clipboard.pixmap()
            if not pixmap.isNull():
                image_item = ImageItem(pixmap=pixmap)
                item = QListWidgetItem("Вставка из буфера")
                item.setIcon(QIcon(pixmap))
                item.setData(Qt.UserRole, image_item)
                self.image_list.insert(0, image_item)
                self.image_list_widget.insertItem(0, item)
                self.image_list_widget.setCurrentRow(0)
                self.current_image_path = None
                self.process_image()
                self.notification("Изображение из буфера вставлено!")
                return

        if mime.hasText():
            text = mime.text().strip()
            if text.startswith("http://") or text.startswith("https://"):
                try:
                    self.download_manga_pages(text)
                    self.notification("Ссылка из буфера обработана как манга!")
                except Exception as e:
                    self.notification(f"Ошибка загрузки по ссылке: {e}")
                return

        if mime.hasUrls():
            urls = sorted(mime.urls(), key=lambda u: natural_key(u.toLocalFile()))
            added_count = 0
            for url in urls:
                path = url.toLocalFile()

                if os.path.isfile(path) and path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_item = ImageItem(path=path)
                    pixmap = QPixmap(path)
                    item = QListWidgetItem(os.path.basename(path))
                    item.setIcon(QIcon(pixmap))
                    item.setData(Qt.UserRole, image_item)
                    self.image_list.append(image_item)
                    self.image_list_widget.addItem(item)
                    added_count += 1

                elif os.path.isdir(path):
                    image_files = sorted([
                        f for f in os.listdir(path)
                        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".webp"))
                    ], key=natural_key)

                    for img_file in image_files:
                        full_path = os.path.join(path, img_file)
                        if not self.is_manga_page(full_path):
                            continue
                        image_item = ImageItem(path=full_path)
                        pixmap = QPixmap(full_path)
                        item = QListWidgetItem(os.path.basename(full_path))
                        item.setIcon(QIcon(pixmap))
                        item.setData(Qt.UserRole, image_item)
                        self.image_list.insert(0, image_item)
                        self.image_list_widget.insertItem(0, item)
                        added_count += 1

            if added_count > 0:
                self.image_list_widget.setCurrentRow(0)
                self.current_image_path = self.image_list[0].path
                self.process_image()
                self.notification(f"Вставлено {added_count} изображений!")
                return

        self.notification("Буфер обмена не содержит изображения, ссылки или папки.")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_J:
            self.toggle_jardic_browser()
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_O:
                self.select_folder()
            elif event.key() == Qt.Key_V:
                self.paste_from_clipboard()
            elif event.key() == Qt.Key_S:
                self.group_content.export_text()
            elif event.key() == Qt.Key_R:
                self.clear_ocr_cache()
                self.notification("Кэш OCR очищен!")
            elif event.key() == Qt.Key_L:
                self.clear_images()
            elif event.key() == Qt.Key_Z:
                self.undo_action()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    def clear_images(self):
        self.notification("Удалено " + str(len(self.image_list)) + " изображений.")
        self.save_history() 
        self.image_list_widget.clear()
        self.image_list.clear()
        self.current_image_path = None
        self.image_label.clear()
        self.text_boxes = []
        self.hovered_text.hide()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if os.path.isdir(path):
                for f in sorted(os.listdir(path), key=natural_key):
                    if f.lower().endswith(('.jpg', '.png', '.jpeg')):
                        paths.append(os.path.join(path, f))
            elif path.lower().endswith(('.jpg', '.png', '.jpeg')):
                paths.append(path)
        if paths:
            self.save_history()
            for p in paths:
                if not any(item.path == p for item in self.image_list):
                    image_item = ImageItem(path=p)
                    self.image_list.append(image_item)
                    pixmap = QPixmap(p)
                    item = QListWidgetItem(os.path.basename(p))
                    item.setIcon(QIcon(pixmap))
                    item.setData(Qt.UserRole, image_item)
                    self.image_list_widget.addItem(item)
            if not self.current_image_path and self.image_list:
                first_item = self.image_list[0]
                self.current_image_path = first_item.path if first_item.path else None
                self.image_list_widget.setCurrentRow(0)
                self.process_image()
            self.notification("Файлы добавлены через drag-and-drop!")

    def export_jardic_html(self): #Дебаг жардика
        def callback(html):
            with open("jardic_export.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("HTML Jardic сохранён в jardic_export.html")
        self.jardic_browser.page().toHtml(callback)

    def setup_jardic_style(self):
        js = """
        (function() {
            // Скрываем только ненужные элементы
            let header = document.querySelector('.section0');
            if(header) header.style.display = 'none';
            let footer = document.querySelector('footer');
            if(footer) footer.style.display = 'none';
            let form1 = document.querySelector('form[name="form1"]');
            if(form1) form1.style.display = 'none';

            // Современный тёмный стиль Jardic
            let css = `
            html, body {
                background: #121212 !important;
                color: #e0e0e0 !important;
                font-family: 'Segoe UI', 'Yu Gothic', Arial, sans-serif !important;
                font-size: 14px !important;
                margin: 0 !important;
                padding: 0 !important;
                height: 100% !important;
                min-height: 100% !important;
            }
                body > *:not(script):not(style) {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }
            .container, .main, .content, .section1, .section2, .section3, .section4, .section5 {
                background: #23242a !important;
                color: #e0e0e0 !important;
                border-radius: 18px !important;
                border: 1.5px solid #292a33 !important;
                padding: 22px 28px !important;
                margin: 22px 0 !important;
                margin: 0 !important;
                transition: bo x-shadow 0.2s, background 0.2s;
            }
            p, td, label, b, div, span {
                color: #e0e0e0 !important;
                font-size: 14px !important;
                line-height: 1.7 !important;
                word-break: break-word !important;
                margin: 0 0 8px 0 !important;
                padding: 0 !important;
            }
            h1, h2, h3, h4 {
                color: #fff !important;
                font-weight: 700 !important;
                margin-top: 18px !important;
                margin-bottom: 12px !important;
            }
            table {
                width: 100% !important;
                background: transparent !important;
                border-collapse: separate !important;
                border-spacing: 0 !important;
                border-radius: 12px !important;
                overflow: hidden !important;
                margin-bottom: 18px !important;
            }
            th, td {
                border: none !important;
                padding: 8px 12px !important;
                background: transparent !important;
            }
            th {
                background: #23242a !important;
                color: #fff !important;
                font-weight: 600 !important;
            }
            tr:nth-child(even) td {
                background: #202127 !important;
            }
            a {
                color: #3a7afe !important;
                text-decoration: none !important;
                transition: color 0.2s;
            }
            a:hover {
                color: #7abaff !important;
                text-decoration: underline !important;
            }
            input, textarea, select {
                background: #18191c !important;
                color: #e0e0e0 !important;
                border: 1px solid #444 !important;
                border-radius: 8px !important;
                padding: 6px 10px !important;
                font-size: 14px !important;
                margin-bottom: 8px !important;
            }
            ::selection {
                background: #3a7afe !important;
                color: #fff !important;
            }
            hr {
                border: none !important;
                border-top: 1px solid #333 !important;
                margin: 18px 0 !important;
            }
            /* Красивое выделение слова Jardic */
            .wordLink[style*="background"], .wordLink.selected {
                outline: 1px solid #3a7afe !important;
                border-radius: 6px !important;
                background: rgba(58, 122, 254, 0.10) !important; /* лёгкая синяя подсветка */
                color: inherit !important;
                box-shadow: 0 0 0 2px #23242a, 0 2px 8px #0002;
                transition: outline 0.15s, box-shadow 0.15s, background 0.15s, color 0.15s;
            }
            /* Скрыть скроллбар, но оставить прокрутку и не менять ширину контента */
            ::-webkit-scrollbar {
                width: 0 !important;
                background: transparent !important;
                display: none !important;
            }
            html, body, .container, .main, .content, .section1, .section2, .section3, .section4, .section5 {
                scrollbar-width: none !important; /* Firefox */
                overflow: overlay !important;     /* Chrome/Edge */
            }
            /* Скрыть футер Jardic и всё, что в нём */
            #footer,
            #footer *,
            div#footer,
            div#footer table,
            div#footer tr,
            div#footer td,
            div#footer a {
                display: none !important;
            }
            /* Скрыть всё после последнего hr (на случай если футер изменится) */
            hr + div,
            hr + table,
            hr + p,
            hr + center,
            hr + span {
                display: none !important;
            }
            /* Скрыть пустые элементы */
            /p:empty, div:empty, td:empty, span:empty {
            /    display: none !important;
            /}
            //* Скругление скроллбара */
            /::-webkit-scrollbar {
            /    width: 10px;
            /    background: #23242a;
            /}
            /::-webkit-scrollbar-thumb {
            /    background: #444;
            /    border-radius: 8px;
            /}
            /::-webkit-scrollbar-thumb:hover {
            /    background: #3a7afe;
            /}
            `;
            let style = document.createElement('style');
            style.innerHTML = css;
            document.head.appendChild(style);
        })();
        """
        self.jardic_browser.page().runJavaScript(js)

    def toggle_jardic_browser(self):
        visible = not self.jardic_browser.isVisible()
        self.jardic_browser.setVisible(visible)

        if visible:
            if self.right_panel.indexOf(self.jardic_wrapper) == -1:
                self.right_panel.addWidget(self.jardic_wrapper, 2)
            self.btn_jardic.setStyleSheet("""
                QPushButton {
                    background-color: #3a7afe;
                    border: 1px solid #3a7afe;
                    color: #fff;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #5591ff;
                    border: 1px solid #5591ff;
                }
            """)
        else:
            if self.right_panel.indexOf(self.jardic_wrapper) != -1:
                self.right_panel.removeWidget(self.jardic_wrapper)
                self.jardic_wrapper.setParent(None)
            self.btn_jardic.setStyleSheet("""
                QPushButton {
                    background-color: #23242a;
                    border: 1px solid #444;
                    color: #e0e0e0;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #2e2f36;
                    border: 1px solid #ff5555;
                }
            """)

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

    def download_manga_dialog(self):
        url, ok = QInputDialog.getText(self, "Скачать мангу", "Введите URL главы или страницы манги:")
        if ok and url:
            try:
                self.download_manga_pages(url)
                QMessageBox.information(self, "Готово", "Страницы успешно загружены!")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось скачать: {e}")

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

    def download_manga_pages(self, url):
        self.notification("Начинается загрузка страниц...")
        self.download_thread = MangaDownloadThread(url)
        self.download_thread.image_ready.connect(self.add_image_to_list)
        self.download_thread.progress.connect(lambda c: self.notification(f"Загружено {c} страниц..."))
        self.download_thread.finished.connect(lambda c: self.notification(f"Загрузка {c} изображений завершена!"))
        self.download_thread.error.connect(lambda msg: self.notification(f"Ошибка: {msg}"))
        self.download_thread.start()

    def add_image_to_list(self, pixmap, name):
        image_item = ImageItem(pixmap=pixmap, name=name)
        item = QListWidgetItem(name)
        item.setIcon(QIcon(pixmap))
        item.setData(Qt.UserRole, image_item)
        self.image_list.append(image_item)
        self.image_list_widget.addItem(item)

    def closeEvent(self, event):
        if hasattr(self, 'ocr_thread') and self.ocr_thread is not None:
            self.ocr_thread.quit()
            self.ocr_thread.wait()
        if hasattr(self, 'batch_thread') and self.batch_thread is not None:
            self.batch_thread.quit()
            self.batch_thread.wait()
        if hasattr(self, 'download_thread') and self.download_thread is not None:
            self.download_thread.quit()
            self.download_thread.wait()
        super().closeEvent(event)

    def clear_ocr_cache(self):
        self.ocr_cache.clear()

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    window = MangaOCRApp()
    window.show()
    sys.exit(app.exec_())
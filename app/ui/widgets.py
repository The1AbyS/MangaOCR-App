from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QHBoxLayout, QListWidget, QTextEdit, QVBoxLayout, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QTextCursor
import cv2
import numpy as np
from ..core.ocr import BatchOCRThread
from ..core.cache import pixmap_md5
from ..core.utils import pixmap_to_cv
from .styles import text_edit_stylesheet, btn_process_stylesheet, btn_export_stylesheet, arrow_button_stylesheet
import os

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

class SmoothListWidget(QListWidget):
    def wheelEvent(self, event):
        scroll_bar = self.verticalScrollBar()
        scroll_bar.setValue(scroll_bar.value() - event.angleDelta().y() // 8)

class TextExportPanel(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.all_text_lines = [] 
        self.page_indices = []
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Здесь появится результат пакетной обработки…")
        self.text_edit.setStyleSheet(text_edit_stylesheet)
        layout.addWidget(self.text_edit)

        self.text_edit.verticalScrollBar().valueChanged.connect(self._update_arrow_positions)
        self.parent_app.image_list_widget.currentRowChanged.connect(self.show_selected_page_text)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_process = QPushButton("Обработать")
        self.btn_process.setStyleSheet(btn_process_stylesheet)

        self.btn_export = QPushButton("Сохранить…")
        self.btn_export.setStyleSheet(btn_export_stylesheet)

        self.btn_fill_frames = QPushButton("Клин…")
        self.btn_fill_frames.setStyleSheet(btn_export_stylesheet)

        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_fill_frames)
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_process)
        layout.addLayout(btn_layout)

        self.btn_process.clicked.connect(self.process_all)
        self.btn_export.clicked.connect(self.export_text)
        self.btn_fill_frames.clicked.connect(self.fill_frames_and_save)

    def imwrite_unicode(self, path, img):
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == '':
                ext = '.png'
                path = path + ext
            success, buf = cv2.imencode(ext, img)
            if not success:
                return False
            with open(path, 'wb') as f:
                f.write(buf.tobytes())
            return True
        except Exception:
            return False

    def fill_frames_and_save(self):
        if not hasattr(self.parent_app, 'image_list') or len(self.parent_app.image_list) == 0:
            QMessageBox.information(self, "Инфо", "Список изображений пуст.")
            return

        out_dir = QFileDialog.getExistingDirectory(self, 'Выберите папку для сохранения')
        if not out_dir:
            return

        if not hasattr(self.parent_app, 'detect_text_boxes'):
            QMessageBox.warning(self, 'Ошибка', 'Функция обнаружения текст-боксов недоступна.')
            return

        self.parent_app.notification('Заливка текст-боксов...')
        for image_item in list(self.parent_app.image_list):
            if getattr(image_item, 'path', None):
                img_cv = self.parent_app.imread_unicode(image_item.path)
                src_name = os.path.splitext(os.path.basename(image_item.path))[0]
            elif getattr(image_item, 'pixmap', None):
                img_cv = pixmap_to_cv(image_item.pixmap)
                src_name = getattr(image_item, 'name', 'image')
            else:
                continue

            if img_cv is None:
                continue

            h, w = img_cv.shape[:2]
            if w != 2560:
                scale = 2560 / float(w)
                new_h = int(h * scale)
                img_resized = cv2.resize(img_cv, (2560, new_h), interpolation=cv2.INTER_AREA)
            else:
                img_resized = img_cv.copy()

            cache_key = None
            if getattr(image_item, 'path', None):
                cache_key = image_item.path
            elif getattr(image_item, 'pixmap', None):
                try:
                    cache_key = pixmap_md5(image_item.pixmap)
                except Exception:
                    cache_key = None

            text_boxes = None
            if cache_key and hasattr(self.parent_app, 'ocr_cache') and cache_key in self.parent_app.ocr_cache:
                try:
                    cached = self.parent_app.ocr_cache[cache_key]
                    if cached:
                        text_boxes = cached[0]
                except Exception:
                    text_boxes = None

            if text_boxes is None:
                try:
                    text_boxes = self.parent_app.detect_text_boxes(img_resized) or []
                except Exception:
                    text_boxes = []
            else:
                try:
                    orig_h, orig_w = img_cv.shape[:2]
                    resized_h, resized_w = img_resized.shape[:2]
                    if orig_w != 0 and resized_w != orig_w:
                        sx = resized_w / float(orig_w)
                        sy = resized_h / float(orig_h)
                    else:
                        sx = sy = 1.0
                    scaled_boxes = []
                    for box in text_boxes:
                        try:
                            if hasattr(box, 'rect'):
                                r = box.rect
                                lx, ty, w_box, h_box = r.left(), r.top(), r.width(), r.height()
                                nx = int(lx * sx)
                                ny = int(ty * sy)
                                nw = max(1, int(w_box * sx))
                                nh = max(1, int(h_box * sy))
                                pts = np.array([[nx, ny], [nx + nw, ny], [nx + nw, ny + nh], [nx, ny + nh]], dtype=np.int32)
                                scaled_boxes.append(pts)
                            elif hasattr(box, 'left') and hasattr(box, 'top') and hasattr(box, 'width'):
                                lx, ty, w_box, h_box = box.left(), box.top(), box.width(), box.height()
                                nx = int(lx * sx)
                                ny = int(ty * sy)
                                nw = max(1, int(w_box * sx))
                                nh = max(1, int(h_box * sy))
                                pts = np.array([[nx, ny], [nx + nw, ny], [nx + nw, ny + nh], [nx, ny + nh]], dtype=np.int32)
                                scaled_boxes.append(pts)
                            else:
                                pts = np.array(box, dtype=np.float32)
                                if pts.ndim == 1 and pts.size == 4:
                                    x0, y0, ww, hh = pts
                                    pts = np.array([[x0 * sx, y0 * sy], [(x0 + ww) * sx, y0 * sy], [(x0 + ww) * sx, (y0 + hh) * sy], [x0 * sx, (y0 + hh) * sy]])
                                else:
                                    pts[:, 0] = (pts[:, 0] * sx)
                                    pts[:, 1] = (pts[:, 1] * sy)
                                scaled_boxes.append(pts.astype(np.int32))
                        except Exception:
                            scaled_boxes.append(box)
                    text_boxes = scaled_boxes
                except Exception:
                    pass

            for box in text_boxes:
                try:
                    pts = np.array(box, dtype=np.int32)
                    x, y, bw, bh = cv2.boundingRect(pts)
                    x1, y1 = x, y
                    x2, y2 = x + bw, y + bh
                    cv2.rectangle(img_resized, (x1, y1), (x2, y2), (255, 255, 255), thickness=-1)
                except Exception:
                    continue

            out_path = os.path.join(out_dir, f"{src_name}_filled.png")
            saved = self.imwrite_unicode(out_path, img_resized)
            if not saved:
                QMessageBox.warning(self, 'Ошибка', f'Не удалось сохранить {out_path}')

        self.parent_app.notification('Готово')

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
                if image_item.path:
                    img_cv = self.parent_app.imread_unicode(image_item.path)
                elif image_item.pixmap:
                    img_cv = pixmap_to_cv(self.image_item.pixmap)
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
                    def is_same_row(f, row):
                        for r in row:
                            top1, bottom1 = f[1], f[1] + f[3]
                            top2, bottom2 = r[1], r[1] + r[3]
                            overlap = min(bottom1, bottom2) - max(top1, top2)
                            if overlap >= -overlap_threshold:
                                return True
                        return False

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

                    rows.sort(key=lambda row: min(f[1] for f in row))
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
                break 
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
        page_idx = self.parent_app.image_list_widget.currentRow()
        if page_idx < 0 or page_idx >= len(self.page_indices):
            return
        start = self.page_indices[page_idx]
        end = self.page_indices[page_idx + 1] if page_idx + 1 < len(self.page_indices) else len(self.all_text_lines)
        for i in range(1, end - start): 
            global_idx = start + i
            if self.line_to_box_idx[global_idx] is None:
                continue
            btn = QPushButton(">", self.text_edit)
            btn.setFixedSize(28, 24)
            btn.setStyleSheet(arrow_button_stylesheet)
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
            if self.parent_app.image_list_widget.currentRow() != image_idx:
                self.parent_app.image_list_widget.setCurrentRow(image_idx)
                self.parent_app.load_selected_image(self.parent_app.image_list_widget.item(image_idx))
            QTimer.singleShot(100, lambda: self.parent_app.highlight_box_by_line(local_box_idx))

    def export_text(self):
        text = "\n".join(self.all_text_lines)
        default_name = "export"
        if self.parent_app.current_image_path:
            folder_path = os.path.dirname(self.parent_app.current_image_path)
            default_name = os.path.basename(folder_path)
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить текст", f"{default_name}.docx", "Документ Word (*.docx);;Текстовый файл (*.txt)")
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
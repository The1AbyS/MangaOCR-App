from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import Qt, QPoint
from pathlib import Path

class TextExportPanel(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setResizeMode(QListWidget.Adjust)
        self._boxes = []
        self._frames = None
        self.current_path = None

    def set_boxes(self, boxes, frames=None, path=None):
        self.clear()
        self._boxes = boxes
        self._frames = frames
        self.current_path = path

        if frames is not None:
            for box in boxes:
                if box.frame_rect is None:
                    for f in frames:
                        if f.rect.contains(box.rect.center()):
                            box.frame_rect = f.rect
                            break

        sorted_boxes = self._sort_boxes(boxes, frames)
        self._boxes = sorted_boxes

        for box in sorted_boxes:
            self.addItem(QListWidgetItem(box.text.strip()))

        self._update_cache()

    def _sort_boxes(self, boxes, frames=None):
        frame_dict = {}
        for box in boxes:
            if hasattr(box, 'frame_rect') and box.frame_rect is not None:
                f = box.frame_rect
                key = (f.left(), f.top(), f.width(), f.height())
                frame_dict.setdefault(key, []).append(box)

        sorted_frame_keys = sort_frames_manga_style(list(frame_dict.keys()))
        sorted_boxes = []
        for key in sorted_frame_keys:
            bxs = frame_dict[key]
            sorted_boxes.extend(sort_boxes_with_tolerance(bxs))

        unframed = [box for box in boxes if not hasattr(box, 'frame_rect') or box.frame_rect is None]
        unframed_sorted = sorted(unframed, key=lambda b: (-b.rect.left(), b.rect.top()))
        sorted_boxes.extend(unframed_sorted)
        return sorted_boxes

    def dropEvent(self, event):
        super().dropEvent(event)

        reordered_texts = [self.item(i).text() for i in range(self.count())]
        text_to_box = {box.text.strip(): box for box in self._boxes}
        new_boxes_ordered = [text_to_box[text] for text in reordered_texts if text in text_to_box]
        self._boxes = new_boxes_ordered

        self._update_cache()

    def _update_cache(self):
        if self.current_path is None:
            return
        wnd = self.window()
        if hasattr(wnd, 'ocr_cache'):
            try:
                frames = self._frames
                wnd.ocr_cache.set_for_path(self.current_path, self._boxes, frames)
            except Exception as e:
                print("Ошибка обновления кэша:", e)

    def get_reordered_texts(self):
        return [self.item(i).text() for i in range(self.count())]

    def _on_context_menu(self, pos: QPoint):
        return

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            item = self.itemAt(event.pos())
            if item is not None:
                wnd = self.window()
                jard = getattr(wnd, 'jardic_widget', None)
                if jard is not None:
                    try:
                        jard.send_text_to_jardic(item.text())
                        act = getattr(wnd, 'jardic_act', None)
                        if act is not None:
                            try:
                                act.setChecked(True)
                            except Exception:
                                pass
                    except Exception:
                        pass
                return
        super().mousePressEvent(event)

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

def sort_boxes_with_tolerance(boxes, x_tolerance=20):
    def box_key(b):
        return (round(-b.rect.left() / x_tolerance), b.rect.top())
    return sorted(boxes, key=box_key)
from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


CHART_COLORS = (
    "#33c2a0",
    "#f2b84b",
    "#5da9e9",
    "#e86f7d",
    "#9b86f1",
    "#6fcf97",
    "#f2994a",
    "#56ccf2",
)


class DonutChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.before = 0
        self.current = 0
        self.after = 0
        self.mode = "progress"
        self.char_counts = []
        self.current_index = -1
        self.setMinimumSize(118, 118)

    def sizeHint(self):
        return QSize(128, 128)

    def set_values(self, before: int, current: int, after: int):
        self.mode = "progress"
        self.before = max(0, before)
        self.current = max(0, current)
        self.after = max(0, after)
        self.update()

    def set_distribution(self, char_counts: list[int], current_index: int):
        self.mode = "distribution"
        self.char_counts = [max(0, count) for count in char_counts]
        self.current_index = current_index
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        side = min(self.width(), self.height()) - 18
        rect = QRectF(
            (self.width() - side) / 2,
            (self.height() - side) / 2,
            side,
            side,
        )

        if self.mode == "distribution":
            self._paint_distribution(painter, rect)
            return

        self._paint_progress(painter, rect)

    def _paint_progress(self, painter: QPainter, rect: QRectF):
        pen = QPen(QColor("#4b4b4b"), 14, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        total = self.before + self.current + self.after
        if total:
            start = 90 * 16
            segments = (
                (self.before, QColor("#33c2a0")),
                (self.current, QColor("#f2b84b")),
                (self.after, QColor("#60646c")),
            )
            for value, color in segments:
                if value <= 0:
                    continue
                span = -round(value / total * 360 * 16)
                pen.setColor(color)
                painter.setPen(pen)
                painter.drawArc(rect, start, span)
                start += span

        percent = round(self.before / total * 100) if total else 0
        painter.setPen(QColor("#f1f1f1"))
        font = QFont()
        font.setPixelSize(25)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, f"{percent}%")

    def _paint_distribution(self, painter: QPainter, rect: QRectF):
        total = sum(self.char_counts)
        pen = QPen(QColor("#4b4b4b"), 14, Qt.SolidLine, Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        if total <= 0:
            painter.setPen(QColor("#cccccc"))
            font = QFont()
            font.setPixelSize(13)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, "Нет текста")
            return

        start = 90 * 16
        for idx, count in enumerate(self.char_counts):
            if count <= 0:
                continue
            color = QColor(CHART_COLORS[idx % len(CHART_COLORS)])
            span = -round(count / total * 360 * 16)
            width = 18 if idx == self.current_index else 14
            pen = QPen(color, width, Qt.SolidLine, Qt.RoundCap)
            painter.setPen(pen)
            painter.drawArc(rect, start, span)
            start += span

        painter.setPen(QColor("#f1f1f1"))
        font = QFont()
        font.setPixelSize(15)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, "Страницы")


class TranslationProgressWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.char_counts = []
        self.page_names = []
        self.current_index = -1

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)

        self.chart = DonutChart(self)
        self.title = QLabel("0%")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-weight: 600; color: #eeeeee;")

        self.current_label = QLabel("Нет данных")
        self.current_label.setAlignment(Qt.AlignCenter)
        self.current_label.setWordWrap(True)
        self.current_label.setStyleSheet("color: #cccccc; font-size: 12px;")

        self.total_label = QLabel("")
        self.total_label.setAlignment(Qt.AlignCenter)
        self.total_label.setWordWrap(True)
        self.total_label.setStyleSheet("color: #999999; font-size: 11px;")

        self.distribution_button = QPushButton("Распределение по страницам")
        self.distribution_button.setCheckable(True)
        self.distribution_button.toggled.connect(self._refresh_labels)

        layout.addWidget(self.chart, 0, Qt.AlignCenter)
        layout.addWidget(self.title)
        layout.addWidget(self.current_label)
        layout.addWidget(self.total_label)
        layout.addWidget(self.distribution_button)

        self.setStyleSheet("""
        TranslationProgressWidget {
            border: 1px solid #444;
            border-radius: 8px;
            background: #2b2b2b;
        }
        """)

    def update_from_cache(self, entries, ocr_cache, current_index: int):
        self.current_index = current_index
        self.char_counts = []
        self.page_names = []

        for path in entries or []:
            count = 0
            self.page_names.append(Path(path).name)
            try:
                cached = ocr_cache.get_for_known_path(path) if ocr_cache is not None else None
            except Exception:
                cached = None

            if cached:
                boxes, frames, md5 = cached
                count = sum(len(getattr(box, "text", "").strip()) for box in boxes)
            self.char_counts.append(count)

        self._refresh_labels()

    def _refresh_labels(self):
        total = sum(self.char_counts)
        has_pages = bool(self.char_counts) and self.current_index >= 0
        self.distribution_button.setEnabled(total > 0)

        if not has_pages:
            self.chart.set_values(0, 0, 0)
            self.title.setText("0% переведено")
            self.current_label.setText("Выберите страницу")
            self.total_label.setText("")
            return

        idx = min(self.current_index, len(self.char_counts) - 1)
        if self.distribution_button.isChecked():
            current = self.char_counts[idx]
            percent = round(current / total * 100) if total else 0
            processed = sum(1 for count in self.char_counts if count > 0)
            self.chart.set_distribution(self.char_counts, idx)
            self.title.setText("Распределение по страницам")
            self.current_label.setText(
                f"{idx + 1} страница: {current} символов ({percent}%)"
            )
            self.total_label.setText(
                f"Обработано {processed}/{len(self.char_counts)} страниц, всего {total} символов"
            )
            self.distribution_button.setText("Показать общий прогресс")
            return

        before = sum(self.char_counts[:idx])
        current = self.char_counts[idx]
        after = max(0, total - before - current)
        percent = round(before / total * 100) if total else 0
        processed = sum(1 for count in self.char_counts if count > 0)

        self.chart.set_values(before, current, after)
        self.title.setText(f"{percent}% переведено")
        self.current_label.setText(
            f"{idx + 1} страница: {current} символов"
        )
        self.total_label.setText(
            f"Обработано {processed}/{len(self.char_counts)} страниц, всего {total} символов"
        )
        self.distribution_button.setText("Распределение по страницам")

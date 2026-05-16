from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen


def draw_overlays(
    pixmap,
    boxes=None,
    frames=None,
    show_frames=False,
    show_numbers_boxes=False,
    ordered_boxes=None,
):
    with QPainter(pixmap) as painter:
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        if frames and show_frames:
            pen = QPen(QColor(0, 200, 0, 180), 3)
            painter.setPen(pen)
            painter.setBrush(QColor(0, 200, 0, 40))

            for frame in frames:
                rect = getattr(frame, "rect", frame)
                painter.drawRect(rect)

        numbered_order = {}
        if show_numbers_boxes:
            source_boxes = ordered_boxes or boxes or []
            for idx, box in enumerate(source_boxes, start=1):
                numbered_order[id(box)] = idx

        if not boxes:
            return

        pen = QPen(QColor(0, 160, 230, 180), 3)
        painter.setPen(pen)
        painter.setBrush(QColor(0, 160, 230, 40))

        metrics = painter.fontMetrics()

        for box in boxes:
            painter.drawRect(box.rect)

            if show_numbers_boxes:
                idx = numbered_order.get(id(box), None)
                if idx is not None:
                    _draw_box_number(painter, box, idx)

            rect = box.rect.adjusted(2, 2, -2, -2)
            elided_text = metrics.elidedText(
                box.text, Qt.ElideRight, rect.width()
            )

            painter.setFont(QFont())
            painter.drawText(
                rect.topLeft() + QPoint(2, metrics.ascent() + 2),
                elided_text
            )


def _draw_box_number(painter: QPainter, box, idx: int):
    num_str = str(idx)
    saved_font = painter.font()
    number_font = QFont(saved_font)
    size_px = max(50, int(min(box.rect.width(), box.rect.height()) * 0.35))
    number_font.setPixelSize(size_px)
    number_font.setBold(True)

    painter.setFont(number_font)
    fm = painter.fontMetrics()
    tw = fm.horizontalAdvance(num_str)
    th = fm.height()
    center = box.rect.center()

    path = QPainterPath()
    path.addText(center.x() - tw / 2, center.y() + th / 4, number_font, num_str)

    painter.save()
    painter.setPen(QPen(QColor(255, 255, 255, 220), 10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(Qt.NoBrush)
    painter.drawPath(path)

    painter.setPen(QPen(QColor(0, 0, 0, 230), 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(QColor(0, 0, 0, 230))
    painter.drawPath(path)
    painter.restore()

    painter.setFont(saved_font)

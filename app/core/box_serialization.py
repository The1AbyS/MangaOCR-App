from PySide6.QtCore import QRect


def box_to_dict(box):
    rect = getattr(box, "rect", None)
    frame_rect = getattr(box, "frame_rect", None)
    text = getattr(box, "text", "")

    return {
        "rect": _rect_to_list(rect),
        "frame_rect": _rect_to_list(frame_rect),
        "text": text,
    }


def box_from_dict(data):
    obj = type("BoxOrFrame", (), {})()
    obj.rect = _rect_from_list(data.get("rect"))
    obj.frame_rect = _rect_from_list(data.get("frame_rect"))
    obj.text = data.get("text", "")
    return obj


def _rect_to_list(rect):
    if rect is None:
        return None
    return [rect.x(), rect.y(), rect.width(), rect.height()]


def _rect_from_list(value):
    if not value:
        return None
    x, y, width, height = value
    return QRect(x, y, width, height)

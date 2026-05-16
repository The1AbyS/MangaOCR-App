from PySide6.QtCore import QTimer


def show_progress(window, text, value=0, maximum=0):
    label = getattr(window, "ocr_progress_label", None)
    bar = getattr(window, "ocr_progress_bar", None)
    if label is None or bar is None:
        return

    label.setText(text)
    label.setVisible(True)
    bar.setRange(0, max(0, maximum))
    bar.setValue(max(0, value))
    bar.setVisible(True)


def update_progress(window, value, maximum, text):
    label = getattr(window, "ocr_progress_label", None)
    bar = getattr(window, "ocr_progress_bar", None)
    if label is None or bar is None:
        return

    label.setText(text)
    if maximum <= 0:
        bar.setRange(0, 0)
    else:
        bar.setRange(0, maximum)
        bar.setValue(min(value, maximum))
    label.setVisible(True)
    bar.setVisible(True)


def hide_progress(window, delay_ms=900):
    label = getattr(window, "ocr_progress_label", None)
    bar = getattr(window, "ocr_progress_bar", None)
    if label is None or bar is None:
        return

    def hide():
        label.setVisible(False)
        bar.setVisible(False)
        bar.setRange(0, 1)
        bar.setValue(0)

    if delay_ms > 0:
        QTimer.singleShot(delay_ms, hide)
    else:
        hide()

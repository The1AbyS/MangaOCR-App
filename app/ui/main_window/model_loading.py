from ...core.threads import ModelsLoadThread


def start_models_load(window):
    window.models_thread = ModelsLoadThread()
    window.models_thread.finished.connect(window.on_models_loaded)
    window.models_thread.error.connect(
        lambda error: window.statusBar().showMessage(f"Ошибка загрузки моделей: {error}")
    )
    window.models_thread.start()


def on_models_loaded(window, mocr, yolo):
    window.mocr = mocr
    window.yolo_detector = yolo
    window.statusBar().showMessage("Модели успешно загружены")

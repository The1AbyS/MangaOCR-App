from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QGraphicsScene,
    QListWidget,
    QProgressBar,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from .docks import create_docks
from ..widgets.image_view import ImageView
from ..widgets.jardic import JardicWidget
from ..widgets.project_manager import ProjectManager
from ..widgets.rawkuma import SearchWindowRawkuma
from ..widgets.text_export_panel import TextExportPanel
from ..widgets.translation_progress import TranslationProgressWidget


def create_widgets(window):
    window.list_widget = QListWidget()
    window.list_widget.itemClicked.connect(window.on_item_clicked)
    window.list_widget.setMinimumWidth(300)
    window.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
    window.list_widget.customContextMenuRequested.connect(window.show_list_menu)

    window.translation_progress = TranslationProgressWidget()

    window.project_manager = ProjectManager()
    window.project_manager.projectOpened.connect(window.load_folder)

    window.text_export_panel = TextExportPanel()

    window.jardic_widget = JardicWidget(window)

    window.scene = None
    window.preview_view = ImageView()

    window.rawkuma_widget = SearchWindowRawkuma()
    window.rawkuma_widget.chapter_clicked.connect(window.action_parser_from_rawkuma)



def create_central(window):
    window.preview_container = QWidget()
    window.preview_layout = QVBoxLayout(window.preview_container)
    window.preview_layout.setContentsMargins(4, 4, 4, 4)

    window.scene = QGraphicsScene()
    window.preview_view.setScene(window.scene)

    window.preview_layout.addWidget(window.preview_view)

    window.central_stack = QStackedWidget()
    window.central_stack.addWidget(window.project_manager)
    window.central_stack.addWidget(window.preview_container)

    window.setCentralWidget(window.central_stack)
    window.central_stack.setCurrentIndex(0)

    create_docks(window)


def create_statusbar(window):
    statusbar = QStatusBar()
    window.setStatusBar(statusbar)

    window.ocr_progress_label = QLabel("")
    window.ocr_progress_label.setStyleSheet("color: #cccccc; padding-left: 8px;")
    window.ocr_progress_label.setVisible(False)

    window.ocr_progress_bar = QProgressBar()
    window.ocr_progress_bar.setFixedWidth(180)
    window.ocr_progress_bar.setFixedHeight(14)
    window.ocr_progress_bar.setTextVisible(False)
    window.ocr_progress_bar.setVisible(False)
    window.ocr_progress_bar.setStyleSheet("""
        QProgressBar {
            border: 1px solid #4b4b4b;
            border-radius: 3px;
            background: #242424;
        }
        QProgressBar::chunk {
            border-radius: 2px;
            background: #6f8fcf;
        }
    """)

    window.version_label = QLabel(window.__version__)
    window.version_label.setStyleSheet("color: gray; padding-right: 10px;")
    statusbar.addPermanentWidget(window.ocr_progress_label)
    statusbar.addPermanentWidget(window.ocr_progress_bar)
    statusbar.addPermanentWidget(window.version_label)

import sys
from PySide6.QtWidgets import QApplication
from app.ui.mainwindow import MainWindow
from PySide6.QtGui import QIcon


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("app/ui/icons/Mocr.png"))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
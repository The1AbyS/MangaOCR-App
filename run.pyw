import sys
from PySide6.QtWidgets import QApplication
from app.ui.mainwindow import MainWindow
from PySide6.QtGui import QFont, QIcon


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("app/ui/icons/Mocr.png"))
    font = QFont()
    font.setFamilies(["Segoe UI", "BIZ UDGothic"])
    app.setFont(font)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
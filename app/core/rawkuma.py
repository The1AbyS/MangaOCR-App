import sys
import re
import requests
from bs4 import BeautifulSoup
from PySide6.QtWidgets import (
    QListWidgetItem, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QListWidget, QLabel, QApplication,
    QPushButton
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer

BASE_URL = "https://rawkuma.net"

class RawKumaWorker(QThread):
    results_ready = Signal(list)  
    chapters_ready = Signal(list) 
    error = Signal(str)

    def __init__(self, session, query=None, manga_url=None):
        super().__init__()
        self.query = query
        self.manga_url = manga_url
        self.session = session

    def get_nonce(self):
        url = f"{BASE_URL}/wp-admin/admin-ajax.php?type=search_form&action=get_nonce"
        headers = {"User-Agent": "Mozilla/5.0", "hx-request": "true"}
        r = self.session.get(url, headers=headers, timeout=15)
        match = re.search(r"value=['\"](.*?)['\"]", r.text)
        if match:
            return match.group(1)
        raise Exception("Nonce not found")

    def get_manga_id(self):
        headers = {"User-Agent": "Mozilla/5.0"}
        r = self.session.get(self.manga_url, headers=headers, timeout=15)
        html = r.text

        match = re.search(r"wp-admin/admin-ajax\.php\?manga_id=(\d+)", html)
        if match:
            return match.group(1)

        raise Exception("Manga ID not found")

    def run(self):
        try:
            if self.query:
                nonce = self.get_nonce()
                search_url = f"{BASE_URL}/wp-admin/admin-ajax.php?nonce={nonce}&action=search"
                headers = {
                    "User-Agent": "Mozilla/5.0",
                    "hx-request": "true",
                    "Content-Type": "application/x-www-form-urlencoded",
                }
                r = self.session.post(search_url, headers=headers, data={"query": self.query}, timeout=15)
                soup = BeautifulSoup(r.text, "html.parser")
                results = []
                for a in soup.find_all("a"):
                    h3 = a.find("h3")
                    if h3:
                        title = h3.get_text(strip=True)
                        link = a.get("href")
                        results.append((title, link))
                self.results_ready.emit(results)

            elif self.manga_url: 
                manga_id = self.get_manga_id()
                url = f"{BASE_URL}/wp-admin/admin-ajax.php?manga_id={manga_id}&page=1&action=chapter_list"
                headers = {"User-Agent": "Mozilla/5.0", "hx-request": "true"}
                r = self.session.get(url, headers=headers, timeout=15)
                soup = BeautifulSoup(r.text, "html.parser")
                chapters = []
                for div in soup.find_all("div", attrs={"data-chapter-number": True}):
                    a = div.find("a", href=True)
                    span = div.find("span")
                    title = span.get_text(strip=True) if span else div.get_text(strip=True)
                    if a:
                        chapters.append((title, a["href"]))
                self.chapters_ready.emit(chapters)

        except Exception as e:
            self.error.emit(str(e))

class SearchWindowRawkuma(QWidget):
    chapter_clicked = Signal(str)
    
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        top_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Введите название манги...")
        top_layout.addWidget(self.search_input)

        self.back_button = QPushButton("Назад")
        self.back_button.clicked.connect(self.go_back)
        
        self.back_button.setFixedHeight(self.search_input.sizeHint().height())
        self.back_button.setFixedWidth(80)   
        self.back_button.hide()           
        top_layout.addWidget(self.back_button)

        layout.addLayout(top_layout)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.open_link)
        layout.addWidget(self.results_list)

        self.session = requests.Session()
        self.worker = None

        self.search_timer = QTimer(self)
        self.search_timer.setInterval(400)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.start_search)
        self.search_input.textChanged.connect(self.on_text_changed)

        self.search_mode = "manga"
        self.saved_results = []
        self.saved_chapters = []
        self.saved_search_text = ""
        self.restoring_results = False

    def start_search(self):
        query = self.search_input.text().strip()
        if not query:
            return

        if self.worker and self.worker.isRunning():
            self.worker.quit()
            self.worker.wait()

        self.results_list.clear()
        self.status_label.setText("Поиск...")
        self.search_mode = "manga"
        self.back_button.hide()

        self.worker = RawKumaWorker(session=self.session, query=query)
        self.worker.results_ready.connect(self.show_results)
        self.worker.error.connect(self.show_error)
        self.worker.start()

    def on_text_changed(self, text):
        text = text.strip()
        if self.search_mode == "chapters":
            if not self.saved_chapters:
                return  

            filtered = [(t, l) for t, l in self.saved_chapters if text.lower() in t.lower()]

            self.results_list.clear()
            for title, link in filtered:
                item = QListWidgetItem(title)
                item.setData(Qt.UserRole, link)
                self.results_list.addItem(item)

        elif self.search_mode == "manga":
            if self.restoring_results:
                self.restoring_results = False
                return
            self.search_timer.start()

    def show_results(self, results):
        self.saved_manga = results  
        self.results_list.clear()
        if not results:
            self.status_label.setText("Ничего не найдено")
            return
        self.status_label.setText(f"Найдено: {len(results)}")
        for title, link in results:
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, link)
            self.results_list.addItem(item)

    def show_chapters(self, chapters):
        self.saved_chapters = chapters 
        self.results_list.clear()

        if not chapters:
            self.status_label.setText("Главы не найдены")
            return

        search_text = self.search_input.text().strip()
        if search_text:
            filtered = [(t, l) for t, l in self.saved_chapters if search_text.lower() in t.lower()]
        else:
            filtered = self.saved_chapters

        for title, link in filtered:
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, link)
            self.results_list.addItem(item)

        self.status_label.setText(f"{self.current_manga_title}, глав: {len(filtered)}")

    def open_link(self, item):
        link = item.data(Qt.UserRole)

        if self.search_mode == "manga":
            self.saved_manga = [(self.results_list.item(i).text(),
                                self.results_list.item(i).data(Qt.UserRole))
                                for i in range(self.results_list.count())]

            self.saved_search_text = self.search_input.text()

            self.current_manga_title = item.text()

            self.search_mode = "chapters"
            self.back_button.show()
            self.search_input.clear()  
            self.results_list.clear()
            self.status_label.setText(f"Загрузка глав... ({self.current_manga_title})")

            if self.worker and self.worker.isRunning():
                self.worker.quit()
                self.worker.wait()

            self.worker = RawKumaWorker(session=self.session, manga_url=link)
            self.worker.chapters_ready.connect(self.show_chapters)
            self.worker.error.connect(self.show_error)
            self.worker.start()

        else:
            self.chapter_clicked.emit(link)

    def go_back(self):
        self.search_mode = "manga"
        self.back_button.hide()
        self.results_list.clear()

        self.restoring_results = True
        self.search_input.setText(self.saved_search_text)

        for title, link in self.saved_manga:
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, link)
            self.results_list.addItem(item)

        self.status_label.setText(f"Найдено: {len(self.saved_manga)}")

    def show_error(self, message):
        self.status_label.setText(f"Ошибка: {message}")
import sys
import requests
from bs4 import BeautifulSoup
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                               QLineEdit, QPushButton, QTextBrowser, QLabel)
from PySide6.QtCore import QThread, Signal, QUrl


class SearchThread(QThread):
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, text):
        super().__init__()
        self.text = text

    def run(self):
        try:
            url = "https://jardic.ru/search/search_r.php"
            params = {"q": self.text, "pg": 0, "sw": 594}

            r = requests.get(url, params=params, timeout=10)
            r.encoding = "utf-8"

            parsed = self.parse_jardic(r.text)
            self.finished.emit(parsed)

        except Exception as e:
            self.error.emit(str(e))

    def parse_jardic(self, html):
        soup = BeautifulSoup(html, "html.parser")

        word_table = soup.find("table", id="tabParsed")
        if word_table:
            words = []
            word_indexes = []

            for a in word_table.find_all("a", class_="wordLink"):
                words.append(a.get_text(strip=True))
                wid = a.get("id", "")
                parts = wid.split("-")
                word_indexes.append(int(parts[1]))

            content = soup.find("table", id="tabContent")
            grouped = {}

            if content:
                for tr in content.find_all("tr"):
                    tr_id = tr.get("id", "")
                    if tr_id.startswith(("trw-", "trd-")):
                        parts = tr_id.split("-")
                        index = int(parts[1])
                        td = tr.find("td")
                        if not td:
                            continue
                        text = td.decode_contents()
                        grouped.setdefault(index, []).append(text)

            result = []
            for word, idx in zip(words, word_indexes):
                entries = grouped.get(idx, [])
                result.append((word, entries))

            return result

        content = soup.find("table", id="tabContent")
        if not content:
            return []

        result = []
        for tr in content.find_all("tr"):
            td = tr.find("td")
            if not td:
                continue
            td_text = td.get_text(" ", strip=True)
            if " - " in td_text:
                word, _ = td_text.split(" - ", 1)
            else:
                word = td_text
            text_html = td.decode_contents()
            result.append((word, [text_html]))

        return result

class JardicWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Введите японский текст")

        self.button = QPushButton("Найти")
        self.button.clicked.connect(self.start_search)

        self.word_browser = QTextBrowser()
        self.word_browser.setMaximumHeight(120)
        self.word_browser.setOpenLinks(False)

        self.result_browser = QTextBrowser()
        self.result_browser.setOpenLinks(False)

        layout.addWidget(self.input)
        layout.addWidget(self.button)
        layout.addWidget(QLabel("Текст:"))
        layout.addWidget(self.word_browser)
        layout.addWidget(QLabel("Перевод:"))
        layout.addWidget(self.result_browser)

        self.word_browser.highlighted.connect(self.on_hover)

        self.data = {}
        self.thread = None

    def send_text_to_jardic(self, text: str):
        self.input.setText(text)
        self.start_search()

    def start_search(self):
        text = self.input.text().strip()
        if not text:
            return

        self.word_browser.setHtml("Загрузка...")
        self.result_browser.clear()

        self.thread = SearchThread(text)
        self.thread.finished.connect(self.show_result)
        self.thread.error.connect(self.show_error)
        self.thread.start()

    def show_result(self, result, active_word=None):
        if not result:
            self.word_browser.setHtml("Ничего не найдено")
            return

        self.data.clear()

        if not active_word:
            active_word = result[0][0]

        html = "<div style='font-size:20px; display:flex; flex-wrap:wrap; gap:10px; line-height:1.25;'>"

        for word, entries in result:
            key = word
            self.data[key] = entries

            if active_word == word:
                bg = "#444"
                color = "#FFD700"
            else:
                bg = "#000"
                color = "#FFF"

            html += f"""
            <a href='{key}' style='
                text-decoration:none;
                color:{color};
                background-color:{bg};
            '>{word}</a>
            """

        html += "</div>"

        self.word_browser.setHtml(html)

        self.show_translation(active_word)

    def on_hover(self, url: QUrl):
        key = url.toString()
        if key in self.data:
            self.show_result(list(self.data.items()), active_word=key)
            self.show_translation(key)

    def show_translation(self, word):
        entries = self.data.get(word, [])
        if not entries:
            self.result_browser.setHtml("<i>Нет данных</i>")
            return

        html = """
        <style>
        body {background-color:#121212; color:white; font-size:16px;}
        hr {border:1px solid #333;}
        span {font-size:14px;}
        </style>
        """
        html += f"<h3 style='color:#4FC3F7'>{word}</h3>"

        for entry in entries:
            soup = BeautifulSoup(entry, "html.parser")
            for span in soup.find_all("span"):
                color = span.get("style", "")
                if "7F0000" in color: 
                    span['style'] = "color:#FF5555;" 
                elif "00007F" in color: 
                    span['style'] = "color:#55AAFF;" 
                elif "000000" in color:
                    span['style'] = "color:#FFFFFF;" 

            html += "<div style='margin-bottom:10px'>" + str(soup) + "</div>"

        self.result_browser.setHtml(html)

    def show_error(self, message):
        self.word_browser.setHtml(f"Ошибка: {message}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = JardicWidget()
    window.input.setText("朝から働き詰めではお体に障られます")
    window.start_search()
    window.show()
    sys.exit(app.exec())
from html import escape

import requests
from bs4 import BeautifulSoup
from PySide6.QtCore import QThread, Signal, QUrl
from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QTextBrowser, QVBoxLayout, QWidget


class SearchThread(QThread):
    result_ready = Signal(object)
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

            parsed = self.parse_jardic(r.text, self.text)
            self.result_ready.emit(parsed)

        except Exception as e:
            self.error.emit(str(e))

    def parse_jardic(self, html, query=""):
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

            word = self._extract_entry_word(td)
            if not word:
                continue

            text_html = td.decode_contents()
            result.append((word, [text_html], self._extract_entry_reading(td)))

        return self._merge_display_results([
            (self._display_word_for_query(word, reading, query), entries)
            for word, entries, reading in self._filter_direct_results(result, query)
        ])

    def _extract_entry_word(self, td):
        spans = td.find_all("span")
        if not spans:
            return ""

        written = self._span_text_by_color(spans, "00007F")
        reading = self._span_text_by_color(spans, "7F0000")
        return written or reading or spans[0].get_text(" ", strip=True)

    def _extract_entry_reading(self, td):
        spans = td.find_all("span")
        return self._span_text_by_color(spans, "7F0000")

    def _span_text_by_color(self, spans, color):
        for span in spans:
            style = span.get("style", "")
            if color not in style.upper():
                continue
            text = span.get_text(" ", strip=True)
            if text:
                return text
        return ""

    def _filter_direct_results(self, results, query):
        query = self._normalize_japanese_text(query)
        if not query or self._has_japanese_separator(query):
            return results

        query_key = self._match_key(query)

        dictionary_forms = self._negative_dictionary_forms(query)
        if dictionary_forms:
            conjugated = [
                result for result in results
                if self._entry_match_keys(result) & dictionary_forms
            ]
            if conjugated:
                return conjugated

        exact = [
            result for result in results
            if query_key in self._entry_match_keys(result)
        ]
        if exact:
            return exact

        single_word_results = [
            result for result in results
            if not self._has_japanese_separator(result[0])
            and not self._has_japanese_separator(result[2])
        ]
        return single_word_results or results

    def _merge_display_results(self, results):
        merged = {}
        for word, entries in results:
            merged.setdefault(word, []).extend(entries)
        return list(merged.items())

    def _entry_match_keys(self, result):
        word, _entries, reading = result
        keys = set()
        for value in (word, reading):
            keys.update(self._form_keys(value))
        return keys

    def _form_keys(self, text):
        normalized = self._normalize_japanese_text(text)
        if not normalized:
            return set()
        forms = {normalized, *normalized.split()}
        return {self._match_key(form) for form in forms if self._match_key(form)}

    def _display_word_for_query(self, word, reading, query):
        query_key = self._match_key(query)
        for value in (word, reading):
            for form in self._normalize_japanese_text(value).split():
                if self._match_key(form) == query_key:
                    return form
        return word

    def _negative_dictionary_forms(self, query):
        if not query.endswith("ない") or len(query) <= 2:
            return set()

        stem = query[:-2]
        forms = {self._match_key(stem + "る")}
        godan_row = {
            "わ": "う", "か": "く", "が": "ぐ", "さ": "す", "ざ": "ず",
            "た": "つ", "だ": "づ", "な": "ぬ", "ば": "ぶ", "ま": "む",
            "ら": "る",
        }
        last = stem[-1]
        if last in godan_row:
            forms.add(self._match_key(stem[:-1] + godan_row[last]))
        return forms

    def _normalize_japanese_text(self, text):
        return " ".join(str(text).replace("\u3000", " ").split())

    def _match_key(self, text):
        ignored = "。、，,.!?！？…・「」『』（）()[]【】“”\"'"
        return "".join(
            char for char in self._normalize_japanese_text(text)
            if char not in ignored and not char.isspace()
        )

    def _has_japanese_separator(self, text):
        return any(char.isspace() for char in self._normalize_japanese_text(text))

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
        self._search_threads = []
        self._next_search_id = 0
        self._active_search_id = None
        self._closing = False

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.stop_searches)

    def send_text_to_jardic(self, text: str):
        self.input.setText(text)
        self.start_search()

    def start_search(self):
        if self._closing:
            return

        text = self.input.text().strip()
        if not text:
            return

        self.word_browser.setHtml("Загрузка...")
        self.result_browser.clear()

        self._next_search_id += 1
        search_id = self._next_search_id
        self._active_search_id = search_id

        thread = SearchThread(text)
        thread.setObjectName(f"jardic-search-{search_id}")
        thread.result_ready.connect(
            lambda result, worker=thread, current_id=search_id: self._finish_search(worker, current_id, result)
        )
        thread.error.connect(
            lambda message, worker=thread, current_id=search_id: self._fail_search(worker, current_id, message)
        )
        thread.finished.connect(lambda worker=thread: self._forget_thread(worker))
        self._search_threads.append(thread)
        thread.start()

    def _finish_search(self, thread, search_id, result):
        if self._closing or search_id != self._active_search_id:
            return
        self.show_result(result)

    def _fail_search(self, thread, search_id, message):
        if self._closing or search_id != self._active_search_id:
            return
        self.show_error(message)

    def _forget_thread(self, thread):
        if thread in self._search_threads:
            self._search_threads.remove(thread)
        if not thread.isRunning():
            thread.deleteLater()

    def stop_searches(self):
        self._closing = True
        for thread in list(self._search_threads):
            self._disconnect_thread(thread)
            thread.requestInterruption()
            if thread.isRunning():
                thread.quit()
                if not thread.wait(12000):
                    thread.terminate()
                    thread.wait(1000)
            self._forget_thread(thread)

    def _disconnect_thread(self, thread):
        for signal in (thread.result_ready, thread.error, thread.finished):
            try:
                signal.disconnect()
            except (RuntimeError, TypeError):
                pass

    def closeEvent(self, event):
        self.stop_searches()
        super().closeEvent(event)

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
            <a href='{escape(key, quote=True)}' style='
                text-decoration:none;
                color:{color};
                background-color:{bg};
            '>{escape(word)}</a>
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

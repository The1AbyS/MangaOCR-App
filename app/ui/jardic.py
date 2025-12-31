from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QUrl
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QTimer
import json


class JardicWidget:
    """Manages an embedded Jardic browser and its container widget.

    Usage:
      jardic = JardicWidget(parent)
      jardic.toggle(splitter)  # show/hide, attaches to splitter when showing
      jardic.send_text_to_jardic(text)  # ensures visible and runs search
    """

    def __init__(self, parent=None):
        self.parent = parent
        self.jardic_browser = QWebEngineView()
        self.jardic_browser.setUrl(QUrl("https://jardic.ru/"))
        self.jardic_browser.setVisible(False)
        self.jardic_browser.setMinimumWidth(300)

        self.jardic_wrapper = QWidget()
        wrapper_layout = QVBoxLayout(self.jardic_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.addWidget(self.jardic_browser)
        try:
            self.jardic_wrapper.setVisible(False)
        except Exception:
            pass

        self._attached_to = None
        self._connected = False
        try:
            self.jardic_browser.loadFinished.connect(lambda ok: self.setup_jardic_style())
            self._connected = True
        except Exception:
            pass

    def setup_jardic_style(self):
        safe_css = json.dumps(jardic_css)  
        js = f"""
        (function() {{
            try {{
                // Скрываем ненужные элементы
                let header = document.querySelector('.section0');
                if (header) header.style.display = 'none';
                let footer = document.querySelector('footer');
                if (footer) footer.style.display = 'none';
                let form1 = document.querySelector('form[name="form1"]');
                if (form1) form1.style.display = 'none';

                // Вставляем стиль (уникальное имя переменной)
                let customStyle = document.createElement('style');
                customStyle.innerHTML = {safe_css};
                document.head.appendChild(customStyle);
            }} catch (e) {{
                console.error("Jardic style injection error:", e);
            }}
        }})();
        """
        self.jardic_browser.page().runJavaScript(js)

    def attach_to_splitter(self, splitter):
        if self._attached_to is splitter:
            return
        try:
            splitter.addWidget(self.jardic_wrapper)
            self._attached_to = splitter
        except Exception:
            try:
                self.jardic_wrapper.setParent(self.parent)
            except Exception:
                pass
            self._attached_to = None

    def detach(self):
        try:
            self.jardic_wrapper.setParent(None)
        except Exception:
            pass
        self._attached_to = None

    def show(self, splitter=None):
        if splitter is not None:
            self.attach_to_splitter(splitter)
        try:
            self.jardic_wrapper.setVisible(True)
        except Exception:
            pass
        self.jardic_browser.setVisible(True)

    def hide(self):
        try:
            self.jardic_browser.setVisible(False)
        except Exception:
            pass
        try:
            self.jardic_wrapper.setVisible(False)
        except Exception:
            pass

    def toggle(self, splitter=None, checked=None):
        visible = self.jardic_browser.isVisible()
        target = (not visible) if checked is None else bool(checked)
        if target:
            self.show(splitter)
        else:
            self.hide()

    def send_text_to_jardic(self, text):
        try:
            splitter = getattr(self.parent, 'splitter', None)
            if not self.jardic_browser.isVisible() and splitter is not None:
                self.show(splitter)
            safe = text.replace('"', '\\"').replace('\n', ' ')
            js = f"""
                (function() {{
                    try {{
                        var input = document.querySelector('input[name="q"]') || document.querySelector('input[type="search"]') || document.querySelector('input[placeholder*="поиск"]');
                        if(input) {{
                            input.focus();
                            input.value = "{safe}";
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            var btn = document.querySelector('button[type="submit"]') || document.querySelector('input[type="submit"]');
                            if(btn) btn.click();
                        }}
                    }} catch(e){{ console.error('Jardic send error', e); }}
                }})();
            """
            self.jardic_browser.page().runJavaScript(js)
        except Exception:
            pass


jardic_css = """
            html, body {
                background: #1e1e1e !important;
                color: #e0e0e0 !important;
                font-family: 'Segoe UI', 'Yu Gothic', Arial, sans-serif !important;
                font-size: 14px !important;
                margin: 0 !important;
                padding: 0 !important;
                height: 100% !important;
                min-height: 100% !important;
            }
                body > *:not(script):not(style) {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }
            .container, .main, .content, .section1, .section2, .section3, .section4, .section5 {
                background: #23242a !important;
                color: #e0e0e0 !important;
                border-radius: 6px !important;
                border: 1px solid #292a33 !important;
                padding: 22px 28px !important;
                margin: 22px 0 !important;
                margin: 0 !important;
                transition: bo x-shadow 0.2s, background 0.2s;
            }
            p, td, label, b, div, span {
                color: #e0e0e0 !important;
                font-size: 14px !important;
                line-height: 1.7 !important;
                word-break: break-word !important;
                margin: 0 0 8px 0 !important;
                padding: 0 !important;
            }
            h1, h2, h3, h4 {
                color: #fff !important;
                font-weight: 700 !important;
                margin-top: 18px !important;
                margin-bottom: 12px !important;
            }
            table {
                width: 100% !important;
                background: transparent !important;
                border-collapse: separate !important;
                border-spacing: 0 !important;
                border-radius: 12px !important;
                overflow: hidden !important;
                margin-bottom: 18px !important;
            }
            th, td {
                border: none !important;
                padding: 8px 12px !important;
                background: transparent !important;
            }
            th {
                background: #23242a !important;
                color: #fff !important;
                font-weight: 600 !important;
            }
            tr:nth-child(even) td {
                background: #202127 !important;
            }
            a {
                color: #3a7afe !important;
                text-decoration: none !important;
                transition: color 0.2s;
            }
            a:hover {
                color: #7abaff !important;
                text-decoration: underline !important;
            }
            input, textarea, select {
                background: #18191c !important;
                color: #e0e0e0 !important;
                border: 1px solid #444 !important;
                border-radius: 8px !important;
                padding: 6px 10px !important;
                font-size: 14px !important;
                margin-bottom: 8px !important;
            }
            ::selection {
                background: #3a7afe !important;
                color: #fff !important;
            }
            hr {
                border: none !important;
                border-top: 1px solid #333 !important;
                margin: 18px 0 !important;
            }
            /* Красивое выделение слова Jardic */
            .wordLink[style*="background"], .wordLink.selected {
                outline: 1px solid #3a7afe !important;
                border-radius: 6px !important;
                background: rgba(58, 122, 254, 0.10) !important; /* лёгкая синяя подсветка */
                color: inherit !important;
                box-shadow: 0 0 0 2px #23242a, 0 2px 8px #0002;
                transition: outline 0.15s, box-shadow 0.15s, background 0.15s, color 0.15s;
            }
            /* Скрыть скроллбар, но оставить прокрутку и не менять ширину контента */
            ::-webkit-scrollbar {
                width: 0 !important;
                background: transparent !important;
                display: none !important;
            }
            html, body, .container, .main, .content, .section1, .section2, .section3, .section4, .section5 {
                scrollbar-width: none !important; /* Firefox */
                overflow: overlay !important;     /* Chrome/Edge */
            }
            /* Скрыть футер Jardic и всё, что в нём */
            #footer,
            #footer *,
            div#footer,
            div#footer table,
            div#footer tr,
            div#footer td,
            div#footer a {
                display: none !important;
            }
            /* Скрыть всё после последнего hr (на случай если футер изменится) */
            hr + div,
            hr + table,
            hr + p,
            hr + center,
            hr + span {
                display: none !important;
            }
            /* Скрыть пустые элементы */
            /p:empty, div:empty, td:empty, span:empty {
            /    display: none !important;
            /}
            //* Скругление скроллбара */
            /::-webkit-scrollbar {
            /    width: 10px;
            /    background: #23242a;
            /}
            /::-webkit-scrollbar-thumb {
            /    background: #444;
            /    border-radius: 8px;
            /}
            /::-webkit-scrollbar-thumb:hover {
            /    background: #3a7afe;
            /}
            `;
            let style = document.createElement('style');
            style.innerHTML = css;
            document.head.appendChild(style);
        })();
        """
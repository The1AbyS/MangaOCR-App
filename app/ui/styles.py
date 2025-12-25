__all__ = ["dark_stylesheet", "mainbg_stylesheet", "btn_select_folder_stylesheet",
           "btn_yolo_model_stylesheet", "yolo_menu_stylesheet", "btn_clear_stylesheet",
           "btn_jardic_stylesheet", "image_list_widget_stylesheet", "satting_and_group_stylesheet",
           "settings_group_panel_stylesheet", "hovered_text_stylesheet", "hovered_img_block_stylesheet",
           "ocr_progress_stylesheet", "jardic_browser_stylesheet", "btn_add_box_stylesheet",
           "btn_del_box_stylesheet", "btn_prev_stylesheet", "btn_next_stylesheet",
           "btn_zoom_block_stylesheet", "btn_add_box_disabled_stylesheet",
           "btn_add_box_enabled_stylesheet", "btn_del_box_disabled_stylesheet",
           "btn_del_box_enabled_stylesheet", "copy_notification_stylesheet",
           "btn_jardic_enabled_stylesheet", "btn_jardic_disabled_stylesheet", "jardic_css",]

dark_stylesheet = """
    QWidget {
        background-color: #121212;
        color: #e0e0e0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        font-size: 14px;
    }
    QPushButton {
        background-color: #1f1f1f;
        border: 1px solid #444;
        padding: 6px;
        border-radius: 10px;
        outline: none;
    }
    QPushButton:hover {
        background-color: #3a3a3a;
        border: 0;
        border-radius: 10px;
        outline: none;
    }
    QPushButton:focus {
        background-color: #1f1f1f;
        border: 1px solid #444;
        outline: none;
    }
    QListWidget {
        background-color: #1e1e1e;
        border: 1px solid #444;
        border-radius: 10px;
        outline: none;
    }
    QListWidget::item:selected {
        background-color: #3a3a3a;
        color: #ffffff;
        border: 0;
        border-radius: 7px;
        outline: none;
    }
    QLabel {
        background-color: #121212;
    }
    QMessageBox {
        background-color: #121212;
        color: #e0e0e0;
    }
"""
text_edit_stylesheet = """
            QTextEdit {
                background: #121212;
                color: #e0e0e0;
                border-radius: 10px;
                border: 1px solid #444;
                font-size: 14px;
                padding: 8px;
                min-height: 120px;
                font-family: "Segoe UI", "Yu Gothic";
            }
            QScrollBar:vertical {
                border: none;
                background: #2e2e2e;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #888888;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """
btn_process_stylesheet = """
            QPushButton {
                background-color: #3a7afe;
                color: #fff;
                border: none;
                border-radius: 8px;
                padding: 5px 16px;
                font-weight: 500;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #5591ff;
            }
        """
btn_export_stylesheet = """
            QPushButton {
                background-color: #23242a;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 8px;
                padding: 5px 16px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #3a7afe;
                color: #fff;
            }
        """ 
arrow_button_stylesheet = """
                QPushButton {
                    color: #3a7afe;
                    border: none;
                    font-size: 18px;
                    font-weight: bold;
                    padding: 0 4px;
                }
                QPushButton:hover {
                    color: #fff;
                }
            """
mainbg_stylesheet = """
            QWidget#MainWindowBg {
                background-color: #121212;
                border-radius: 20px;
                border: 1px solid #222;
            }
        """
btn_select_folder_stylesheet = """
            QPushButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #00bfff;
            }
        """
btn_yolo_model_stylesheet = """
            QToolButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
                color: #e0e0e0;
                font-size: 15px;
                padding: 0 18px;
            }
            QToolButton::menu-indicator {
                image: none;
                width: 0px;
            }
            QMenu {
                background-color: #23242a;
                color: #e0e0e0;
                border-radius: 8px;
                font-size: 15px;
            }
            QMenu::item:selected {
                background-color: #2e2f36;
                border: 1px solid #3a7afe;
            }
        """
yolo_menu_stylesheet = """
            QMenu {
                background-color: #23242a;
                color: #e0e0e0;
                border: 1px solid #444;
                border-radius: 10px;
                padding: 6px 0;
                font-size: 15px;
                font-family: 'Segoe UI', 'Yu Gothic', Arial, sans-serif;
            }
            QMenu::item {
                background: transparent;
                padding: 8px 24px 8px 24px;
                border-radius: 8px;
                margin: 2px 8px;
            }
            QMenu::item:selected {
                background-color: #3a7afe;
                color: #fff;
            }
            QMenu::separator {
                height: 1px;
                background: #444;
                margin: 4px 8px;
            }
        """
btn_clear_stylesheet = """
            QPushButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #ff5555;
            }
        """
btn_jardic_stylesheet = """
            QPushButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #3a7afe;
            }
        """
image_list_widget_stylesheet = """
            QScrollBar:vertical {
                border: none;
                background: #2e2e2e;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #555555;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical:hover {
                background: #888888;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """
satting_and_group_stylesheet = """
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #e0e0e0;
                    font-weight: bold;
                    padding: 5px;
                    text-align: center;
                }
                QPushButton:hover {
                    color: #ffffff;
                }
            """
settings_group_panel_stylesheet = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 10px;
                margin-top: 6px;
            }
        """
hovered_text_stylesheet = """
            background-color: #2e2e2e;
            color: #ffffff;
            padding: 6px 10px;
            border: 1px solid #555555;
            outline: none;
            border-radius: 10px;
            font-size: 14px;
            font-family: "Yu Gothic";
        """
hovered_img_block_stylesheet = """
            border: 2px solid #3a7afe;
            border-radius: 8px;
            background: #18191c;
        """
ocr_progress_stylesheet = """
            QProgressBar {
                background: #222;
                color: #fff;
                border-radius: 10px;
                border: 1px solid #444;
                font-size: 11px;
                padding: 1px 6px;
            }
            QProgressBar::chunk {
                background: #3a7afe;
                border-radius: 8px;
            }
        """
jardic_browser_stylesheet = """
            border-radius: 20px;
            background: transparent;
        """
btn_add_box_stylesheet = """
            QPushButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #3a7afe;
            }
        """
btn_del_box_stylesheet = """
            QPushButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #ff5555;
            }
        """
btn_prev_stylesheet = """
            QPushButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #3a7afe;
            }
        """
btn_next_stylesheet = """
            QPushButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #3a7afe;
            }
        """
btn_zoom_block_stylesheet = """
            QPushButton {
                background-color: #23242a;
                border: 1px solid #444;
                border-radius: 8px;
                font-size: 18px;
            }
            QPushButton:hover {
                background-color: #2e2f36;
                border: 1px solid #3a7afe;
            }
        """
btn_add_box_disabled_stylesheet = """
                QPushButton {
                    background-color: #23242a;
                    border: 1px solid #444;
                    color: #e0e0e0;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #2e2f36;
                    border: 1px solid #3a7afe;
                }
            """
btn_add_box_enabled_stylesheet = """
                QPushButton {
                    background-color: #3a7afe;
                    border: 2px solid #3a7afe;
                    color: #fff;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #5591ff;
                    border: 2px solid #5591ff;
                }
            """
btn_del_box_disabled_stylesheet = """
                QPushButton {
                    background-color: #23242a;
                    border: 1px solid #444;
                    color: #e0e0e0;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #2e2f36;
                    border: 1px solid #ff5555;
                }
            """
btn_del_box_enabled_stylesheet = """
                QPushButton {
                    background-color: #ff5555;
                    border: 2px solid #ff5555;
                    color: #fff;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #ff8888;
                    border: 2px solid #ff8888;
                }
            """
copy_notification_stylesheet = """
                background-color: #1e1e1e;
                color: white;
                padding: 8px 15px;
                border-radius: 10px;
                font-size: 15px;
                border: 1px solid #444;
            """
btn_jardic_enabled_stylesheet = """
                QPushButton {
                    background-color: #3a7afe;
                    border: 1px solid #3a7afe;
                    color: #fff;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #5591ff;
                    border: 1px solid #5591ff;
                }
            """
btn_jardic_disabled_stylesheet = """
                QPushButton {
                    background-color: #23242a;
                    border: 1px solid #444;
                    color: #e0e0e0;
                    border-radius: 8px;
                }
                QPushButton:hover {
                    background-color: #2e2f36;
                    border: 1px solid #5591ff;
                }
            """
jardic_css = """
            html, body {
                background: #121212 !important;
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
                border-radius: 18px !important;
                border: 1.5px solid #292a33 !important;
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
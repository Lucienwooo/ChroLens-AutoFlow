# -*- coding: utf-8 -*-
import re
import requests
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QTextBrowser, QPushButton, QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices, QColor

class LinkSearchWorker(QThread):
    progress_signal = pyqtSignal(int, int) # current, total
    result_signal = pyqtSignal(str, str)   # original_code, found_url
    finished_signal = pyqtSignal()

    def __init__(self, text_input):
        super().__init__()
        # 使用正則表達式分割，支援換行、空格、逗號
        self.raw_codes = re.split(r'[\s,\n]+', text_input)
        # 過濾掉空字串並去重 (保留順序)
        self.codes = []
        seen = set()
        for code in self.raw_codes:
            clean_code = code.strip()
            if clean_code and clean_code.upper() not in seen:
                self.codes.append(clean_code)
                seen.add(clean_code.upper())
                
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def run(self):
        total = len(self.codes)
        for i, code in enumerate(self.codes):
            self.progress_signal.emit(i + 1, total)
            
            # 使用增強的邏輯來嘗試獲取下載連結
            result_url = self.find_download_link(code)
            
            if result_url:
                self.result_signal.emit(code, result_url)
            else:
                # 若都失敗，直接搜尋
                url_search = f"https://javmix.tv/?s={code}"
                self.result_signal.emit(code, url_search)

        self.finished_signal.emit()

    def find_download_link(self, code):
        """嘗試找到該番號的直接下載頁面連結 (advertape/streamtape)"""
        candidates = self.generate_candidates(code)
        
        for url in candidates:
            try:
                # 使用正常的 GET 請求來獲取頁面內容
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200:
                    # 嘗試從回應中提取 streamtape/advertape 連結
                    stream_link = self.extract_stream_link(resp.text)
                    if stream_link:
                        # 找到直接下載連結
                        return stream_link
                    else:
                        # 找不到播放器連結，退而求其次返回 javmix 頁面連結
                        return url
            except:
                continue
        return None

    def generate_candidates(self, code):
        """生成可能的 JavMix 頁面網址"""
        candidates = []
        code_upper = code.upper()
        
        # 1. FC2 處理
        fc2_match = re.search(r'(?i)fc2-ppv-(\d+)', code)
        if fc2_match:
            num = fc2_match.group(1)
            # JavMix 常見的 FC2 網址結構
            candidates.append(f"https://javmix.tv/fc2ppv/fc2-ppv-{num}/")
            candidates.append(f"https://javmix.tv/fc2ppv/fc2ppv-{num}/")
            return candidates # FC2 格式較固定，優先處理

        # 2. 一般番號處理
        general_match = re.search(r'(?i)([a-z]+)[-_]?(\d+)', code)
        if general_match:
            code_alpha = general_match.group(1).lower()
            code_num = general_match.group(2)
            base_code = f"{code_alpha}-{code_num}"
            
            # 常見結構
            candidates.append(f"https://javmix.tv/video/{base_code}/")
            candidates.append(f"https://javmix.tv/xvideo/x_{base_code}/")
            candidates.append(f"https://javmix.tv/video/{code.lower()}/") # 嘗試原始格式
        
        return candidates

    def extract_stream_link(self, html):
        """從 HTML 中提取 Streamtape/Advertape 連結"""
        # 嘗試匹配 iframe src
        # <iframe src="https://streamtape.com/e/JJaygzDp9LSjjqM/" ...>
        # <iframe src="//advertape.net/e/JJaygzDp9LSjjqM/" ...>
        # 注意: 網頁上的 embed code 通常是 /e/ 而不是 /v/，但下載頁面通常是 /v/
        
        patterns = [
            r'(?:src=["\']|href=["\'])(https?:)?//(?:advertape\.net|streamtape\.com|advers\.net)/[ev]/([a-zA-Z0-9]+)',
            r'document\.getElementById\(\'ideoooolink\'\)\.innerHTML\s*=\s*[\'"](.*?)[\'"]' # 有些網站會藏在 script 中
        ]
        
        for p in patterns:
            match = re.search(p, html)
            if match:
                # 若是匹配到直接連結
                if "src" in p or "href" in p:
                    video_id = match.group(2)
                    return f"https://advertape.net/v/{video_id}/"
                
                # 若是 script 中的情形 (視具體網頁結構而定，目前先針對 iframe src)
                
        return None

    def check_url(self, url):
        """僅檢查 URL 是否有效 (HEAD 請求)"""
        try:
            resp = self.session.head(url, timeout=5, allow_redirects=True)
            return resp.status_code == 200
        except:
            return False

class LinkSearchDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JavMix 快速搜尋工具")
        self.resize(600, 500)
        self.setStyleSheet("""
            QDialog { background-color: #1C1C1E; color: #E5E5EA; }
            QLabel { color: #E5E5EA; font-size: 14px; }
            QTextEdit, QTextBrowser { 
                background-color: #2C2C2E; 
                color: #E5E5EA; 
                border: 1px solid #3A3A3C; 
                border-radius: 4px; 
                padding: 5px;
            }
            QPushButton {
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #0066CC; }
            QPushButton:disabled { background-color: #3A3A3C; color: #8E8E93; }
            QProgressBar {
                background-color: #2C2C2E;
                border: none;
                height: 4px;
                border-radius: 2px;
            }
            QProgressBar::chunk { background-color: #34C759; border-radius: 2px; }
        """)
        
        layout = QVBoxLayout(self)
        
        # 輸入區
        layout.addWidget(QLabel("貼上番號："))
        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("例如:\nFC2-PPV-1764780\nHRSM-132-UB\nSNOS-104")
        layout.addWidget(self.input_text, 1)
        
        # 操作區
        btn_layout = QHBoxLayout()
        self.search_btn = QPushButton("開始搜尋")
        self.search_btn.clicked.connect(self.start_search)
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setStyleSheet("background-color: #3A3A3C;")
        self.clear_btn.clicked.connect(lambda: self.input_text.clear())
        
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.search_btn)
        layout.addLayout(btn_layout)
        
        # 進度條
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        layout.addWidget(self.progress)
        
        # 輸出區
        layout.addWidget(QLabel("搜尋結果 (點擊開啟):"))
        self.result_text = QTextBrowser()
        self.result_text.setReadOnly(True)
        layout.addWidget(self.result_text, 1)
        
        self.worker = None

    def start_search(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "請先輸入番號!")
            return
            
        self.search_btn.setEnabled(False)
        self.result_text.clear()
        self.progress.setValue(0)
        
        self.worker = LinkSearchWorker(text)
        self.worker.progress_signal.connect(self.update_progress)
        self.worker.result_signal.connect(self.add_result)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def update_progress(self, current, total):
        self.progress.setMaximum(total)
        self.progress.setValue(current)

    def add_result(self, code, url):
        # 建立 HTML 連結格式
        html = f'<div style="margin-bottom: 4px;">' \
               f'<span style="color: #FF9500; font-weight: bold;">{code}</span>: ' \
               f'<a href="{url}" style="color: #007AFF; text-decoration: none;">{url}</a>' \
               f'</div>'
        self.result_text.append(html)

    def on_finished(self):
        self.search_btn.setEnabled(True)
        # 讓 QTextEdit 支援點擊連結
        self.result_text.setOpenExternalLinks(True) 
        # self.result_text.anchorClicked.connect(self.open_link)
        QMessageBox.information(self, "完成", "搜尋已完成!")

    def open_link(self, url):
        QDesktopServices.openUrl(url)

# -*- coding: utf-8 -*-
import re
import requests
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QTextEdit, QTextBrowser, QPushButton, QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices, QColor

class LinkSearchWorker(QThread):
    progress_signal = pyqtSignal(int, int) # current, total
    result_signal = pyqtSignal(str, str, str, str, str)   # original_code, origin_vid, origin_dl, mosaic_vid, mosaic_dl
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
            
            # 使用雙重搜尋邏輯：獲取無碼(Origin)與有碼(Mosaic)的影片與下載連結
            results = self.find_javmix_dual_links(code)
            
            self.result_signal.emit(code, results['origin_vid'], results['origin_dl'], results['mosaic_vid'], results['mosaic_dl'])

        self.finished_signal.emit()

    def find_javmix_dual_links(self, code):
        """嘗試找到無碼(Origin)與有碼(Mosaic)的連結組合"""
        results = {
            'origin_vid': "", 'origin_dl': "",
            'mosaic_vid': "", 'mosaic_dl': ""
        }
        
        # 定義候選網址群
        origin_candidates = []
        mosaic_candidates = []
        
        # FC2 通常只有 Origin
        fc2_match = re.search(r'(?i)fc2-ppv-(\d+)', code)
        if fc2_match:
            num = fc2_match.group(1)
            origin_candidates.append(f"https://javmix.tv/fc2ppv/fc2-ppv-{num}/")
            origin_candidates.append(f"https://javmix.tv/fc2ppv/fc2ppv-{num}/")
        else:
            # 一般番號處理
            general_match = re.search(r'(?i)([a-z]+)[-_]?(\d+)', code)
            if general_match:
                code_alpha = general_match.group(1).lower()
                code_num = general_match.group(2)
                base_code = f"{code_alpha}-{code_num}"
                
                # Origin 候選
                origin_candidates.append(f"https://javmix.tv/video/{base_code}/")
                origin_candidates.append(f"https://javmix.tv/video/{code.lower()}/")
                
                # Mosaic 候選 (含 x_)
                mosaic_candidates.append(f"https://javmix.tv/xvideo/x_{base_code}/")
                mosaic_candidates.append(f"https://javmix.tv/xvideo/x_{code.lower()}/")

        # 搜尋 Origin
        for url in origin_candidates:
            try:
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200:
                    results['origin_vid'] = url
                    dl_link = self.extract_download_page_link(resp.text, code)
                    if dl_link:
                        results['origin_dl'] = dl_link
                    break
            except:
                pass
                
        # 搜尋 Mosaic
        for url in mosaic_candidates:
            try:
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200:
                    results['mosaic_vid'] = url
                    dl_link = self.extract_download_page_link(resp.text, code)
                    if dl_link:
                        results['mosaic_dl'] = dl_link
                    break
            except:
                pass
                
        # 右側補償：若都沒有找到頁面，為了格式完整回傳假連結，但在顯示端不加超連結 (由 video_url 判定)
        return results

    def extract_download_page_link(self, html, code):
        """從 HTML 中提取下載跳轉頁面連結 (基於 Automa 分析出的 Selector 與 JS Unpacking)"""
        # ==========================
        # 混淆的 javascript eval() 區塊，直接解碼找出 iplayerhls.com 或 streamtape.com
        # ==========================
        eval_match = re.search(r'return p}\(\'(.*?)\',(\d+),(\d+),\'(.*?)\'\.split', html, re.DOTALL)
        if eval_match:
            try:
                p, a, c, k = eval_match.groups()
                a = int(a)
                c = int(c)
                k = k.split('|')
                
                def decode(val, base):
                    chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                    if val < base:
                        return chars[val]
                    return decode(val // base, base) + chars[val % base]
                
                for i in range(c - 1, -1, -1):
                    if k[i]:
                        encoded = decode(i, a)
                        p = re.sub(r'\b' + encoded + r'\b', k[i], p)
                
                m_v = re.search(r'href=["\'](https?://(?:iplayerhls\.com|streamtape\.com|advertape\.net|callistanise\.com|dintezuvio\.com)/(?:v|f|d|download)/([^"\']+)?)["\']', p)
                if m_v:
                    return self.extract_final_mp4_link(m_v.group(1), code)
                
                # B. 播放器連結 (href="https://streamtape.com/e/...")
                m_e = re.search(r'href=["\'](https?://(?:iplayerhls\.com|streamtape\.com|advertape\.net|callistanise\.com|dintezuvio\.com)/e/([^"\']+)?)["\']', p)
                if m_e:
                    return self.extract_final_mp4_link(m_e.group(1), code)

            except Exception as e:
                pass
                
        # ==========================
        # 若無 JS 混淆，嘗試從網頁原始碼一般提取
        # ==========================
        m_v = re.search(r'href=["\'](https?://(?:iplayerhls\.com|streamtape\.com|advertape\.net|callistanise\.com|dintezuvio\.com)/(?:v|f|d|download)/([^"\']+)?)["\']', html)
        if m_v:
            return self.extract_final_mp4_link(m_v.group(1), code)
            
        m_e = re.search(r'href=["\'](https?://(?:iplayerhls\.com|streamtape\.com|advertape\.net|callistanise\.com|dintezuvio\.com)/e/([^"\']+)?)["\']', html)
        if m_e:
            return self.extract_final_mp4_link(m_e.group(1), code)

        return None

    def extract_final_mp4_link(self, player_url, code):
        """從播放器頁面擷取最終 CDN 下載路由端點 (_h)。
        CDN 的 _h URL 在瀏覽器訪問時會透過 302 Redirect 動態產生帶有合法時效簽章的 .mp4?t=...。
        hls2 的 t= 簽章只對 M3U8 串流路徑有效，強行嫁接到 vp/*.mp4 路徑只會得到 403 Forbidden。"""
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        try:
            # 依賴伺服器特性路由：
            # - callistanise / dintezuvio 原始碼放在 /f/ 裡 
            # - StreamHG / iPlayerhls 原始碼放在 /e/ 裡
            is_calli_type = 'callistanise' in player_url or 'dintezuvio' in player_url
            if is_calli_type:
                target_url = player_url.replace('/v/', '/f/').replace('/e/', '/f/').replace('/d/', '/f/').replace('/download/', '/f/')
            else:
                target_url = player_url.replace('/v/', '/e/').replace('/f/', '/e/').replace('/d/', '/e/').replace('/download/', '/e/')
            
            resp = self.session.get(target_url, headers=headers, timeout=10)
            if resp.status_code == 200:
                html = resp.text
                
                # 方法一：Streamtape / StreamHG / Callistanise JS 解包與 HLS 轉換 MP4 直鏈 (可抓到防盜鏈 Query)
                eval_match = re.search(r'eval\(function\(p,a,c,k,e,d\)\{.*?return p\}\(\'(.*?)\',\s*(\d+),\s*(\d+),\s*\'(.*?)\'\.split\(\'\|\'\)', html, re.DOTALL)
                if eval_match:
                    p, a, c, k = eval_match.groups()
                    a = int(a)
                    c = int(c)
                    k = k.split('|')
                    
                    def decode(val, base):
                        chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                        if val < base:
                            return chars[val]
                        return decode(val // base, base) + chars[val % base]

                    for i in range(c - 1, -1, -1):
                        if k[i]:
                            encoded = decode(i, a)
                            p = re.sub(r'\b' + encoded + r'\b', k[i], p)
                            
                    # 從 hls2 URL 提取 CDN 域名 + 視頻路徑，轉換成 _h 路由器端點
                    # hls2: https://SUB.acek-cdn.com/hls2/01/07472/VIDEOID_x/master.m3u8?t=HLS_TOKEN
                    # _h:   https://SUB.acek-cdn.com/vp/01/07472/VIDEOID_h
                    # 瀏覽器訪問 _h 時 CDN 會產生新鮮的 302 Redirect 給 .mp4?t=DL_TOKEN
                    hls_match = re.search(r'"hls2"\s*:\s*"(https?://[^"]+)"', p)
                    if hls_match:
                        hls_url = hls_match.group(1)
                        domain_m = re.search(r'(https?://[^/]+)', hls_url)
                        path_m = re.search(r'/hls2(/.*?/)([a-zA-Z0-9]+)_', hls_url)
                        
                        if domain_m and path_m:
                            domain = domain_m.group(1)
                            folder = path_m.group(1)
                            vid = path_m.group(2)
                            # 返回 _h 路由端點 (不含 .mp4 後綴或 hls2 的簽章)
                            return f"{domain}/vp{folder}{vid}_h"
                            
                # 備用：直接在 HTML 中搜尋含 _h 的 /vp/ 路徑
                token_match = re.search(r'"(/vp/[^"]+_h)"', html)
                if token_match:
                    vp_path = token_match.group(1)
                    domain_match = re.search(r'"(https?://[a-zA-Z0-9.-]+\.(?:premilkyway|cdn-centaurus|acek-cdn)\.com)"', html)
                    if domain_match:
                        return domain_match.group(1) + vp_path
                    
        except Exception:
            pass
            
        # 若直鏈抓取失敗，退回到下載跳轉頁 (有廣告倒數，但仍可下載)
        backup_link = player_url.replace('/e/', '/download/').replace('/v/', '/download/').replace('/f/', '/download/')
        if not backup_link.endswith('_h'):
            backup_link = backup_link + '_h'
        return backup_link

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

    def add_result(self, code, origin_vid, origin_dl, mosaic_vid, mosaic_dl):
        # 建立 Origin 區塊
        if origin_vid:
            origin_base = f'<a href="{origin_vid}" style="color: #007AFF; text-decoration: none;">Origin</a>'
        else:
            origin_base = '<span style="color: #8E8E93;">Origin</span>'
            
        if origin_dl:
            origin_dl_html = f'<a href="{origin_dl}" style="color: #007AFF; text-decoration: none;">下載</a>'
        else:
            origin_dl_html = '<span style="color: #8E8E93;">(無下載)</span>'
            
        # 建立 Mosaic 區塊
        if mosaic_vid:
            mosaic_base = f'<a href="{mosaic_vid}" style="color: #007AFF; text-decoration: none;">Mosaic</a>'
        else:
            mosaic_base = '<span style="color: #8E8E93;">Mosaic</span>'
            
        if mosaic_dl:
            mosaic_dl_html = f'<a href="{mosaic_dl}" style="color: #007AFF; text-decoration: none;">下載</a>'
        else:
            mosaic_dl_html = '<span style="color: #8E8E93;">(無下載)</span>'
            
        # 要求的格式: snos-096_Origin_下載_/_Mosaic_下載
        html = f'<div style="margin-bottom: 4px;">' \
               f'<span style="color: #FF9500; font-weight: bold;">{code}</span>_' \
               f'{origin_base}_{origin_dl_html}_/_{mosaic_base}_{mosaic_dl_html}' \
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

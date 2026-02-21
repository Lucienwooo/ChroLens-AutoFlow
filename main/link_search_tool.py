# -*- coding: utf-8 -*-
import re
import requests
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QProgressBar, QMessageBox, QSplitter, QScrollArea,
    QWidget, QFrame, QFileDialog, QApplication, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QUrl, QMimeData, QSize
from PyQt6.QtGui import QDesktopServices, QPixmap, QCursor

try:
    from javmix_downloader import (
        get_hls_from_download_url, DownloadWorker, DownloadItemWidget
    )
    _HAS_DOWNLOADER = True
except ImportError:
    _HAS_DOWNLOADER = False

import hashlib, tempfile
from pathlib import Path

_PLAYER_HOSTS = (
    'iplayerhls.com', 'streamtape.com', 'advertape.net',
    'callistanise.com', 'dintezuvio.com'
)
_PLAYER_PAT = '|'.join(re.escape(h) for h in _PLAYER_HOSTS)

CARD_W = 240
CARD_H = 135

# 縮圖磁碟目錄（TEMP/autoflow_thumbs）
_THUMB_CACHE = Path(tempfile.gettempdir()) / 'autoflow_thumbs'
_THUMB_CACHE.mkdir(exist_ok=True)

def _thumb_cache_path(url: str) -> Path:
    return _THUMB_CACHE / (hashlib.md5(url.encode()).hexdigest() + '.jpg')


# ─────────────────────────────────────────────────────────────
# 自訂 QTextEdit：貼上時保留換行格式
# ─────────────────────────────────────────────────────────────
class MultilineTextEdit(QTextEdit):
    def insertFromMimeData(self, source: QMimeData):
        if source.hasText():
            raw = source.text()
            normalized = (
                raw.replace('\r\n', '\n')
                   .replace('\r', '\n')
                   .replace('\u2028', '\n')
                   .replace('\u2029', '\n')
            )
            self.insertPlainText(normalized)
        else:
            super().insertFromMimeData(source)


# ─────────────────────────────────────────────────────────────
# 橫向捲動區（滑鼠滾輪 → 橫向）
# ─────────────────────────────────────────────────────────────
class HScrollArea(QScrollArea):
    def wheelEvent(self, event):
        bar = self.horizontalScrollBar()
        bar.setValue(bar.value() - int(event.angleDelta().y() * 0.8))


# ─────────────────────────────────────────────────────────────
# 縮圖非同步下載執行緒
# ─────────────────────────────────────────────────────────────
class ThumbnailFetcher(QThread):
    # (image_bytes, actress_name)
    done = pyqtSignal(bytes, str)

    def __init__(self, vid_url: str):
        super().__init__()
        self.vid_url = vid_url

    def run(self):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Referer': 'https://javmix.tv/'
            }

            actress = ''
            img_url = None
            html    = ''

            # 检查磁碟（女優名別另存在同名 .txt）
            cache_img  = _thumb_cache_path(self.vid_url)
            cache_info = cache_img.with_suffix('.txt')

            if cache_img.exists() and cache_img.stat().st_size > 1000:
                img_bytes = cache_img.read_bytes()
                actress   = cache_info.read_text(encoding='utf-8') if cache_info.exists() else ''
                self.done.emit(img_bytes, actress)
                return

            # 擷取頁面
            r = requests.get(self.vid_url, headers=headers, timeout=8)
            if r.status_code == 200:
                html = r.text

                # 擷取女優名（從 og:description 的【出演者】）
                desc_m = re.search(r'<meta[^>]+(?:name|property)=["\'](?:description|og:description)["\'][^>]+content=["\']([^"\']{0,400})["\']',
                                   html, re.IGNORECASE)
                if desc_m:
                    act_m = re.search(r'【出演者】([^【\s]{1,40})', desc_m.group(1))
                    if act_m:
                        actress = act_m.group(1).strip()

                # 策略 1： HTML 已下載 — 找圖片
                for pat in [
                    r'<img[^>]+src=["\']([^"\']*/mono/movie[^"\']*)["\'\s]',
                    r'href=["\']([^"\']*/mono/movie/adult/[^"\']*)["\'\s]',
                    r'<img[^>]+src=["\']([^"\']+pl\.jpe?g[^"\']*)["\']',
                ]:
                    m = re.search(pat, html, re.IGNORECASE)
                    if m:
                        img_url = m.group(1)
                        if img_url.startswith('//'):
                            img_url = 'https:' + img_url
                        break

            # 策略 2：從番號推導 DMM 封面 URL
            if not img_url:
                slug_m = re.search(
                    r'/(?:video|xvideo)/(?:x_)?([a-z0-9][a-z0-9\-]+?)(?:-ub)?/?$',
                    self.vid_url)
                if slug_m:
                    raw = slug_m.group(1)
                    if not raw.startswith('fc2'):
                        code_nd = raw.replace('-', '')
                        img_url = f'https://pics.dmm.co.jp/mono/movie/adult/{code_nd}/{code_nd}pl.jpg'

            if not img_url:
                return

            ir = requests.get(img_url, headers=headers, timeout=8)
            if ir.status_code == 200 and len(ir.content) > 1000:
                # 寫入磁碟
                cache_img.write_bytes(ir.content)
                cache_info.write_text(actress, encoding='utf-8')
                self.done.emit(ir.content, actress)
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────
# 搜尋結果卡片 Widget
# ─────────────────────────────────────────────────────────────
class ResultCard(QFrame):
    download_requested = pyqtSignal(str, str, bool)  # code, dl_url, is_mosaic

    def __init__(self, code, o_vid, o_dl, m_vid, m_dl):
        super().__init__()
        self.code  = code
        self.o_vid = o_vid
        self.o_dl  = o_dl
        self.m_vid = m_vid
        self.m_dl  = m_dl

        self.setFixedWidth(CARD_W)
        self.setStyleSheet("""
            QFrame {
                background: #2C2C2E;
                border-radius: 8px;
                border: 1px solid #3A3A3C;
            }
            QFrame:hover { border: 1px solid #636366; }
            QPushButton {
                background: transparent; color: #30D158;
                border: none; font-size: 16px; padding: 0 2px;
            }
            QPushButton:hover { color: #34D058; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(0, 0, 0, 8)

        # 縮圖
        self.thumb = QLabel()
        self.thumb.setFixedSize(CARD_W, CARD_H)
        self.thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb.setStyleSheet('background:#1C1C1E; border-radius:8px 8px 0 0; border:none;')
        self.thumb.setText('⏳')
        layout.addWidget(self.thumb)

        # 底部資訊區
        info = QWidget()
        info.setStyleSheet('background:transparent;')
        il = QVBoxLayout(info)
        il.setSpacing(4)
        il.setContentsMargins(10, 0, 10, 0)

        # 番號
        code_lbl = QLabel(code)
        code_lbl.setStyleSheet('color:#FF9500; font-weight:bold; font-size:13px; background:transparent; border:none;')
        code_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        il.addWidget(code_lbl)

        # 女優標簽（待綺圖擷取後填入）
        self.actress_lbl = QLabel('')
        self.actress_lbl.setStyleSheet(
            'color:#8E8E93; font-size:11px; background:transparent; border:none;')
        self.actress_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.actress_lbl.setWordWrap(True)
        il.addWidget(self.actress_lbl)

        # 連結行
        links_row = QHBoxLayout()
        links_row.setSpacing(6)
        self._add_link_btn(links_row, 'Origin', o_vid, o_dl, is_mosaic=False)
        sep = QLabel('│')
        sep.setStyleSheet('color:#3A3A3C; background:transparent; border:none;')
        links_row.addWidget(sep)
        self._add_link_btn(links_row, 'Ai解碼', m_vid, m_dl, is_mosaic=True)
        links_row.addStretch()
        il.addLayout(links_row)

        layout.addWidget(info)

        # 啟動縮圖下載（優先 origin，備用 mosaic）
        thumb_vid = o_vid or m_vid
        if thumb_vid:
            self._fetcher = ThumbnailFetcher(thumb_vid)
            self._fetcher.done.connect(self._set_thumb)
            self._fetcher.start()

    def _add_link_btn(self, row, label, vid_url, dl_url, is_mosaic):
        # 標題連結
        lbl = QLabel(label)
        color = '#5E5CE6' if is_mosaic else '#007AFF'
        if vid_url:
            lbl.setStyleSheet(f'color:{color}; text-decoration:underline; background:transparent; border:none; font-size:12px;')
            lbl.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            lbl.mousePressEvent = lambda e, u=vid_url: QDesktopServices.openUrl(QUrl(u))
        else:
            lbl.setStyleSheet('color:#636366; background:transparent; border:none; font-size:12px;')
        row.addWidget(lbl)

        # 下載按鈕
        if dl_url and _HAS_DOWNLOADER:
            dl_btn = QPushButton('⬇')
            dl_btn.setFixedSize(22, 22)
            dl_btn.setToolTip('直接下載到本機')
            dl_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            dl_btn.clicked.connect(lambda checked, c=self.code, u=dl_url, m=is_mosaic:
                                   self.download_requested.emit(c, u, m))
            row.addWidget(dl_btn)
        elif dl_url:
            dl_icon = QLabel('⬇')
            dl_icon.setStyleSheet('color:#007AFF; background:transparent; border:none;')
            dl_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            dl_icon.mousePressEvent = lambda e, u=dl_url: QDesktopServices.openUrl(QUrl(u))
            row.addWidget(dl_icon)
        else:
            no = QLabel('◌')
            no.setStyleSheet('color:#3A3A3C; background:transparent; border:none;')
            row.addWidget(no)

    def _set_thumb(self, data: bytes, actress: str):
        px = QPixmap()
        if px.loadFromData(data):
            px = px.scaled(CARD_W, CARD_H,
                           Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                           Qt.TransformationMode.SmoothTransformation)
            x = (px.width()  - CARD_W) // 2
            y = (px.height() - CARD_H) // 2
            px = px.copy(x, y, CARD_W, CARD_H)
            self.thumb.setPixmap(px)
            self.thumb.setText('')
        if actress:
            self.actress_lbl.setText(actress)


# ─────────────────────────────────────────────────────────────
# JS eval 解包工具
# ─────────────────────────────────────────────────────────────
def _js_decode(val: int, base: int) -> str:
    chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if val < base:
        return chars[val]
    return _js_decode(val // base, base) + chars[val % base]


def _unpack_eval(html: str) -> str | None:
    m = re.search(
        r"eval\(function\(p,a,c,k,e,d\)\{.*?return p\}\('(.*?)',\s*(\d+),\s*(\d+),\s*'(.*?)'\.split\('\|'\)",
        html, re.DOTALL
    )
    if not m:
        return None
    try:
        p, a, c, k = m.groups()
        a, c = int(a), int(c)
        k = k.split('|')
        for i in range(c - 1, -1, -1):
            if k[i]:
                p = re.sub(r'\b' + _js_decode(i, a) + r'\b', k[i], p)
        return p
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────
# 搜尋工作執行緒
# ─────────────────────────────────────────────────────────────
class LinkSearchWorker(QThread):
    progress_signal = pyqtSignal(int, int)
    result_signal   = pyqtSignal(str, str, str, str, str)
    finished_signal = pyqtSignal()

    def __init__(self, text_input: str):
        super().__init__()
        self.text_input = text_input
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def run(self):
        codes = [l.strip().upper() for l in re.split(r'[\n\r]+', self.text_input) if l.strip()]
        total = len(codes)
        for i, code in enumerate(codes):
            self.progress_signal.emit(i + 1, total)
            try:
                r = self.find_javmix_dual_links(code)
                self.result_signal.emit(code,
                    r.get('origin_vid',''), r.get('origin_dl',''),
                    r.get('mosaic_vid',''), r.get('mosaic_dl',''))
            except Exception:
                self.result_signal.emit(code, '', '', '', '')
        self.finished_signal.emit()

    def find_javmix_dual_links(self, code: str) -> dict:
        result = {'origin_vid':'', 'origin_dl':'', 'mosaic_vid':'', 'mosaic_dl':''}
        c = code.lower().replace('_', '-')

        def _origin_urls(c):
            urls = [f'https://javmix.tv/video/{c}/', f'https://javmix.tv/video/{c}-ub/']
            if 'fc2' in c:
                no_dash = c.replace('fc2-ppv-', 'fc2ppv-').replace('fc2-', 'fc2')
                num_m = re.search(r'(\d{5,})', c)
                num = num_m.group(1) if num_m else None
                extra = []
                if no_dash != c:
                    extra += [f'https://javmix.tv/video/{no_dash}/',
                              f'https://javmix.tv/fc2ppv/{no_dash}/']
                if num:
                    extra += [f'https://javmix.tv/video/fc2ppv-{num}/',
                              f'https://javmix.tv/fc2ppv/fc2ppv-{num}/']
                urls = extra + urls
            return list(dict.fromkeys(urls))

        def _mosaic_urls(c):
            urls = [f'https://javmix.tv/xvideo/x_{c}/', f'https://javmix.tv/xvideo/x_{c}-ub/']
            if 'fc2' in c:
                no_dash = c.replace('fc2-ppv-', 'fc2ppv-').replace('fc2-', 'fc2')
                num_m = re.search(r'(\d{5,})', c)
                num = num_m.group(1) if num_m else None
                if no_dash != c:
                    urls.insert(1, f'https://javmix.tv/xvideo/x_{no_dash}/')
                if num:
                    urls.append(f'https://javmix.tv/xvideo/x_fc2ppv-{num}/')
            return urls

        for url in _origin_urls(c):
            try:
                r = self.session.get(url, timeout=10, allow_redirects=True)
                is_valid = r.status_code == 200 and any(
                    seg in r.url for seg in ('/video/', '/fc2ppv/', '/xvideo/')
                ) and 'javmix.tv' in r.url
                if is_valid:
                    result['origin_vid'] = r.url
                    dl = self.extract_download_page_link(r.text, code)
                    if dl:
                        result['origin_dl'] = dl
                    break
            except Exception:
                pass

        for url in _mosaic_urls(c):
            try:
                r = self.session.get(url, timeout=10, allow_redirects=True)
                if r.status_code == 200 and '/xvideo/' in r.url:
                    result['mosaic_vid'] = r.url
                    dl = self.extract_download_page_link(r.text, code)
                    if dl:
                        result['mosaic_dl'] = dl
                    break
            except Exception:
                pass

        return result

    def extract_download_page_link(self, html: str, code: str) -> str | None:
        unpacked = _unpack_eval(html)
        if unpacked:
            link = self._find_player_link(unpacked, code)
            if link:
                return link
        return self._find_player_link(html, code)

    def _find_player_link(self, text: str, code: str) -> str | None:
        m = re.search(
            r'href=["\']'
            r'(https?://(?:' + _PLAYER_PAT + r')'
            r'/(?:v|f|d|download)/[^"\'<>\s]+)'
            r'["\']', text)
        if m:
            return self.extract_final_mp4_link(m.group(1), code)
        m = re.search(
            r'href=["\']'
            r'(https?://(?:' + _PLAYER_PAT + r')'
            r'/e/[^"\'<>\s]+)'
            r'["\']', text)
        if m:
            return self.extract_final_mp4_link(m.group(1), code)
        m = re.search(
            r'src=["\']'
            r'(https?://(?:' + _PLAYER_PAT + r')'
            r'/(?:v|e|f|d|download|embed)/[^"\'<>\s]+)'
            r'["\']', text)
        if m:
            return self.extract_final_mp4_link(m.group(1), code)
        return None

    def extract_final_mp4_link(self, player_url: str, code: str) -> str:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        try:
            is_calli = any(d in player_url for d in ('callistanise', 'dintezuvio'))
            if is_calli:
                target = re.sub(r'/(?:v|e|d|download)/', '/f/', player_url)
                if '/f/' not in target:
                    target = player_url
            else:
                target = re.sub(r'/(?:v|f|d|download)/', '/e/', player_url)
                if '/e/' not in target:
                    target = player_url

            resp = self.session.get(target, headers=headers, timeout=10)
            if resp.status_code != 200:
                raise ValueError(f'HTTP {resp.status_code}')

            unpacked = _unpack_eval(resp.text)
            if unpacked:
                hls_m = re.search(r'"hls2"\s*:\s*"(https?://[^"]+)"', unpacked)
                if hls_m:
                    path_m = re.search(r'/hls2/[^/]+/[^/]+/([a-zA-Z0-9]+)_', hls_m.group(1))
                    if path_m:
                        from urllib.parse import urlparse
                        pd = urlparse(target)
                        return f'{pd.scheme}://{pd.netloc}/download/{path_m.group(1)}_h'
                vp_m = re.search(r'"(/vp/[^"]+_h)"', unpacked)
                if vp_m:
                    vid_m2 = re.search(r'/vp/[^/]+/[^/]+/([a-zA-Z0-9]+)_h', vp_m.group(1))
                    if vid_m2:
                        from urllib.parse import urlparse
                        pd = urlparse(target)
                        return f'{pd.scheme}://{pd.netloc}/download/{vid_m2.group(1)}_h'
        except Exception:
            pass

        backup = re.sub(r'/(?:e|v|f|d|embed)/', '/download/', player_url)
        if not backup.endswith('_h'):
            backup = backup.rstrip('/') + '_h'
        return backup


# ─────────────────────────────────────────────────────────────
# 備用 DownloadItemWidget
# ─────────────────────────────────────────────────────────────
if not _HAS_DOWNLOADER:
    class DownloadItemWidget(QFrame):
        cancel_clicked = pyqtSignal(object)
        def __init__(self, code, download_url, output_path):
            super().__init__()
            QVBoxLayout(self).addWidget(QLabel(f'[!] {code} — pip install yt-dlp'))
        def start_download(self): pass
        def cancel(self): pass
        @property
        def status_label(self):
            class _L:
                text = lambda s: '❌'
            return _L()


# ─────────────────────────────────────────────────────────────
# 整合版：搜尋 + 下載管理器
# ─────────────────────────────────────────────────────────────
class LinkSearchDialog(QDialog):
    _STYLE = """
        QDialog  { background-color: #1C1C1E; color: #E5E5EA; }
        QLabel   { color: #E5E5EA; font-size: 13px; }
        QTextEdit {
            background-color: #2C2C2E; color: #E5E5EA;
            border: 1px solid #3A3A3C; border-radius: 6px; padding: 6px;
        }
        QPushButton {
            background-color: #007AFF; color: white;
            border: none; border-radius: 5px;
            padding: 6px 14px; font-weight: bold;
        }
        QPushButton:hover    { background-color: #0066CC; }
        QPushButton:disabled { background-color: #3A3A3C; color: #636366; }
        QProgressBar {
            background-color: #2C2C2E; border: none;
            height: 4px; border-radius: 2px;
        }
        QProgressBar::chunk { background-color: #34C759; border-radius: 2px; }
        QSplitter::handle   { background-color: #3A3A3C; height: 2px; }
        QScrollArea         { border: none; background: transparent; }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('AutoFlow 番號搜尋與下載')
        self.resize(720, 720)
        self.setStyleSheet(self._STYLE)

        self.worker          = None
        self._download_map   = {}
        self._download_items = []
        self._output_dir     = __import__('pathlib').Path.home() / 'Downloads'
        self._result_cards   = []

        self._init_ui()

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(12, 12, 12, 12)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # ══ 上半：搜尋面板 ══
        top = QWidget()
        tl  = QVBoxLayout(top)
        tl.setSpacing(7)
        tl.setContentsMargins(0, 0, 0, 6)

        hdr = QLabel('番號資訊')
        hdr.setStyleSheet('font-size: 15px; font-weight: bold; color: #FFFFFF;')
        tl.addWidget(hdr)

        self.input_text = MultilineTextEdit()
        self.input_text.setPlaceholderText('每行一個番號，例如：\nFC2-PPV-1764780\nDVMM-357\nSNOS-104')
        self.input_text.setMaximumHeight(100)
        tl.addWidget(self.input_text)

        btn_row = QHBoxLayout()
        self.clear_btn = QPushButton('清空')
        self.clear_btn.setStyleSheet('background:#3A3A3C; font-weight:normal;')
        self.clear_btn.clicked.connect(lambda: self.input_text.clear())
        self.search_btn = QPushButton('開始搜尋')
        self.search_btn.clicked.connect(self.start_search)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch()
        btn_row.addWidget(self.search_btn)
        tl.addLayout(btn_row)

        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        tl.addWidget(self.progress)

        res_hdr = QLabel(
            '搜尋結果&nbsp;&nbsp;'
            '<span style="color:#8E8E93;font-size:11px;">'
            '標題 = 開啟網頁&nbsp;／&nbsp;綠色 ⬇ = 直接下載到本機&nbsp;／&nbsp;滾輪左右滑'
            '</span>'
        )
        res_hdr.setTextFormat(Qt.TextFormat.RichText)
        tl.addWidget(res_hdr)

        # 橫向卡片捲動區
        self._card_scroll = HScrollArea()
        self._card_scroll.setWidgetResizable(True)
        self._card_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._card_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._card_scroll.setStyleSheet("""
            QScrollArea { background: #2C2C2E; border: 1px solid #3A3A3C; border-radius: 6px; }
            QScrollBar:horizontal {
                height: 4px; background: #2C2C2E; border-radius: 2px;
            }
            QScrollBar::handle:horizontal {
                background: #3A3A3C; border-radius: 2px; min-width: 30px;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
        """)
        self._card_scroll.setMinimumHeight(CARD_H + 80)

        self._card_host = QWidget()
        self._card_host.setStyleSheet('background: transparent;')
        self._card_row  = QHBoxLayout(self._card_host)
        self._card_row.setSpacing(10)
        self._card_row.setContentsMargins(10, 8, 10, 8)
        self._card_row.addStretch()   # 靠左排列

        self._card_scroll.setWidget(self._card_host)
        tl.addWidget(self._card_scroll, 1)

        # 空白提示
        self._empty_lbl = QLabel('搜尋後結果將顯示於此')
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet('color:#636366; font-size:13px; background:transparent;')
        self._card_row.insertWidget(0, self._empty_lbl)

        splitter.addWidget(top)

        # ══ 下半：下載管理面板 ══
        bot = QWidget()
        bl  = QVBoxLayout(bot)
        bl.setSpacing(7)
        bl.setContentsMargins(0, 6, 0, 0)

        dl_hdr_row = QHBoxLayout()
        dl_hdr = QLabel('下載佇列')
        dl_hdr.setStyleSheet('font-size: 15px; font-weight: bold; color: #FFFFFF;')

        self.dir_btn = QPushButton('儲存至')
        self.dir_btn.setStyleSheet('background:#3A3A3C; font-weight:normal; padding:4px 10px;')
        self.dir_btn.clicked.connect(self._choose_dir)

        self.dir_label = QLabel(str(self._output_dir))
        self.dir_label.setStyleSheet('color:#636366; font-size:11px;')
        self.dir_label.setWordWrap(True)

        self.clear_done_btn = QPushButton('清除已完成')
        self.clear_done_btn.setStyleSheet('background:#3A3A3C; font-weight:normal; padding:4px 10px;')
        self.clear_done_btn.clicked.connect(self._clear_done)

        dl_hdr_row.addWidget(dl_hdr)
        dl_hdr_row.addWidget(self.dir_btn)
        dl_hdr_row.addWidget(self.dir_label, 1)
        dl_hdr_row.addWidget(self.clear_done_btn)
        bl.addLayout(dl_hdr_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet('QScrollArea{background:#1C1C1E;}')
        self._queue_host = QWidget()
        self._queue_host.setStyleSheet('background:#1C1C1E;')
        self._queue_layout = QVBoxLayout(self._queue_host)
        self._queue_layout.setSpacing(6)
        self._queue_layout.addStretch()
        scroll.setWidget(self._queue_host)
        bl.addWidget(scroll, 1)

        if not _HAS_DOWNLOADER:
            warn = QLabel('[!] yt-dlp 未安裝，執行 pip install yt-dlp 後重啟')
            warn.setStyleSheet('color:#FF9F0A; font-size:11px;')
            bl.addWidget(warn)

        splitter.addWidget(bot)
        splitter.setSizes([360, 280])
        root.addWidget(splitter)

    # ── 搜尋 ─────────────────────────────────────────────────
    def start_search(self):
        text = self.input_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, '提示', '請先輸入番號！')
            return
        self.search_btn.setEnabled(False)
        self.progress.setValue(0)
        self._download_map.clear()

        # 清空舊卡片
        self._empty_lbl.hide()
        for card in self._result_cards:
            self._card_row.removeWidget(card)
            card.deleteLater()
        self._result_cards.clear()

        self.worker = LinkSearchWorker(text)
        self.worker.progress_signal.connect(self._update_progress)
        self.worker.result_signal.connect(self._add_result)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.start()

    def _update_progress(self, cur, total):
        self.progress.setMaximum(total)
        self.progress.setValue(cur)

    def _add_result(self, code, o_vid, o_dl, m_vid, m_dl):
        self._download_map[code] = {'origin_dl': o_dl, 'mosaic_dl': m_dl}

        card = ResultCard(code, o_vid, o_dl, m_vid, m_dl)
        card.download_requested.connect(self._enqueue)
        # 插入到 stretch 前
        self._card_row.insertWidget(self._card_row.count() - 1, card)
        self._result_cards.append(card)

    def _on_finished(self):
        self.search_btn.setEnabled(True)
        if not self._result_cards:
            self._empty_lbl.show()
            self._empty_lbl.setText('找不到相關影片')

    # ── 下載佇列 ─────────────────────────────────────────────
    def _choose_dir(self):
        d = QFileDialog.getExistingDirectory(self, '選擇儲存資料夾', str(self._output_dir))
        if d:
            self._output_dir = __import__('pathlib').Path(d)
            self.dir_label.setText(d)

    def _enqueue(self, code: str, download_url: str, is_mosaic: bool = False):
        filename = f'MOSAIC-{code}.mp4' if is_mosaic else f'{code}.mp4'
        out_path = str(self._output_dir / filename)
        item = DownloadItemWidget(code, download_url, out_path)
        item.cancel_clicked.connect(self._on_cancel)
        self._queue_layout.insertWidget(self._queue_layout.count() - 1, item)
        self._download_items.append(item)
        item.start_download()

    def _on_cancel(self, item):
        item.cancel()

    def _clear_done(self):
        for item in list(self._download_items):
            try:
                txt = item.status_label.text()
            except Exception:
                txt = ''
            if any(k in txt for k in ('完成', '❌', '取消', '已取消')):
                self._queue_layout.removeWidget(item)
                item.deleteLater()
                self._download_items.remove(item)

    # ── 向後相容 ─────────────────────────────────────────────
    def update_progress(self, c, t): self._update_progress(c, t)
    def add_result(self, *a):        self._add_result(*a)
    def on_finished(self):           self._on_finished()

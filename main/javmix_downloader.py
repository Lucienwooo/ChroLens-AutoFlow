# -*- coding: utf-8 -*-
"""
Javmix HLS Download Manager
整合到 AutoFlow 的下載管理器，支援 HLS 串流下載
"""
import re
import sys
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import requests
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QProgressBar, QScrollArea, QWidget, QFrame,
    QFileDialog, QApplication, QMessageBox
)
from PyQt6.QtGui import QFont


# ============================================================
# HLS 提取邏輯 (從 javmix_dl.py 移植)
# ============================================================

def _decode_js(val, base):
    chars = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if val < base:
        return chars[val]
    return _decode_js(val // base, base) + chars[val % base]


def get_hls2_url(player_url: str) -> str | None:
    """從播放器頁面 eval() JS 提取完整 HLS M3U8 URL（含有效 t= 簽章）"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    is_calli = any(d in player_url for d in ('callistanise', 'dintezuvio'))
    target = re.sub(r'/(?:v|e|d|download)/', '/f/', player_url) if is_calli else \
             re.sub(r'/(?:v|f|d|download)/', '/e/', player_url)

    try:
        resp = requests.get(target, headers=headers, timeout=12)
        if resp.status_code != 200:
            return None
        html = resp.text
    except Exception:
        return None

    eval_m = re.search(
        r'eval\(function\(p,a,c,k,e,d\)\{.*?return p\}\(\'(.*?)\',\s*(\d+),\s*(\d+),\s*\'(.*?)\'\.split\(\'\|\'\)',
        html, re.DOTALL
    )
    if not eval_m:
        return None

    p, a, c, k = eval_m.groups()
    a, c = int(a), int(c)
    k = k.split('|')
    for i in range(c - 1, -1, -1):
        if k[i]:
            p = re.sub(r'\b' + _decode_js(i, a) + r'\b', k[i], p)

    hls_m = re.search(r'"hls2"\s*:\s*"(https?://[^"]+\.m3u8[^"]*)"', p)
    return hls_m.group(1) if hls_m else None


def get_hls_from_download_url(download_page_url: str) -> tuple[str | None, str | None]:
    """
    從 /download/{vid}_h 格式的 URL 推導出播放器 embed URL，
    然後提取 HLS M3U8 URL。
    Returns: (hls2_url, player_url)
    """
    vid_m = re.search(r'/download/([a-zA-Z0-9]+)_h', download_page_url)
    if not vid_m:
        return None, None

    vid = vid_m.group(1)
    parsed = urlparse(download_page_url)
    domain_base = f'{parsed.scheme}://{parsed.netloc}'

    for route in ['/e/', '/f/']:
        player_url = f'{domain_base}{route}{vid}'
        hls2_url = get_hls2_url(player_url)
        if hls2_url:
            return hls2_url, player_url

    return None, None


# ============================================================
# 下載工作執行緒
# ============================================================

class DownloadWorker(QThread):
    progress_signal    = pyqtSignal(float, str)   # (percent 0-100, speed_str)
    finished_signal    = pyqtSignal(bool, str)    # (success, message)
    destination_signal = pyqtSignal(str)          # actual output file path

    def __init__(self, hls_url: str, output_path: str, referer: str = None):
        super().__init__()
        self.hls_url = hls_url
        self.output_path = output_path
        self.referer = referer
        self._stop = False

    def stop(self):
        self._stop = True
        self.terminate()

    def run(self):
        cmd = [
            sys.executable, '-m', 'yt_dlp',
            '--no-warnings', '--no-playlist',
            '--hls-prefer-native',
            '-f', 'bestvideo+bestaudio/best',   # 明確選最高畫質
            '--merge-output-format', 'mp4',      # 強制合併成 mp4
            '--newline',
            '-o', self.output_path,
        ]
        if self.referer:
            cmd += ['--add-header', f'Referer:{self.referer}']
        cmd.append(self.hls_url)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,  # 分離 stderr 供錯誤報告用
                text=True, encoding='utf-8', errors='replace'
            )
            stderr_lines = []

            import threading
            def _read_stderr():
                for ln in proc.stderr:
                    stderr_lines.append(ln.strip())
            t = threading.Thread(target=_read_stderr, daemon=True)
            t.start()

            for line in proc.stdout:
                if self._stop:
                    proc.terminate()
                    self.finished_signal.emit(False, '已取消')
                    return
                # 解析進度
                m = re.search(r'\[download\]\s+([\d.]+)%.*?at\s+([^\s]+)', line)
                if m:
                    self.progress_signal.emit(float(m.group(1)), m.group(2))
                # 解析實際輸出路徑 (e.g. [download] Destination: C:\...\file.mp4)
                d = re.search(r'\[download\]\s+Destination:\s+(.+)', line.strip())
                if d:
                    self.destination_signal.emit(d.group(1).strip())

            proc.wait()
            t.join(timeout=2)

            if proc.returncode == 0:
                self.finished_signal.emit(True, self.output_path)
            else:
                # 取得最後一行有意義的錯誤訊息
                err_lines = [l for l in stderr_lines if l and not l.startswith('[')]
                err_msg = err_lines[-1] if err_lines else (stderr_lines[-1] if stderr_lines else f'exit {proc.returncode}')
                self.finished_signal.emit(False, f'{err_msg[:80]}')
        except FileNotFoundError:
            self.finished_signal.emit(False, '找不到 yt-dlp，請執行 pip install yt-dlp')
        except Exception as e:
            self.finished_signal.emit(False, str(e))


# ============================================================
# 單一下載項目 Widget
# ============================================================

class DownloadItemWidget(QFrame):
    cancel_clicked = pyqtSignal(object)

    def __init__(self, code: str, download_url: str, output_path: str):
        super().__init__()
        self.code = code
        self.download_url = download_url
        self.output_path = output_path
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame { background-color: #2C2C2E; border-radius: 8px; padding: 6px; }
            QLabel { color: #E5E5EA; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)

        # 頂部: 番號 + 取消按鈕
        top = QHBoxLayout()
        self.code_label = QLabel(f'<b style="color:#FF9500">{self.code}</b>')
        self.code_label.setTextFormat(Qt.TextFormat.RichText)
        self.status_label = QLabel('準備中...')
        self.status_label.setStyleSheet('color: #8E8E93; font-size: 12px;')
        self.cancel_btn = QPushButton('✕')
        self.cancel_btn.setFixedSize(24, 24)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #2C2C2E;
                color: white;
                border: 1.5px solid #FF3B30;
                border-radius: 12px;
                font-weight: bold;
                font-size: 13px;
                padding: 0;
            }
            QPushButton:hover { background: #FF3B30; color: white; }
        """)
        self.cancel_btn.clicked.connect(lambda: self.cancel_clicked.emit(self))
        top.addWidget(self.code_label)
        top.addWidget(self.status_label, 1)
        top.addWidget(self.cancel_btn)
        layout.addLayout(top)

        # 進度條
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background:#3A3A3C; border-radius:3px; }
            QProgressBar::chunk { background:#30D158; border-radius:3px; }
        """)
        layout.addWidget(self.progress_bar)

        # 路徑標籤 — 若為 yt-dlp 樣板路徑，顯示目錄而不是樣板字串
        import os as _os
        display_path = (
            _os.path.dirname(self.output_path) + _os.sep + '(yt-dlp 自動命名)'
            if '%(' in self.output_path else self.output_path
        )
        self.path_label = QLabel(f'→ {display_path}')
        self.path_label.setStyleSheet('color:#636366; font-size: 11px;')
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)

    def start_download(self):
        """解析 HLS URL 並啟動下載"""
        self.status_label.setText('正在取得串流網址...')

        class HlsFetcher(QThread):
            done = pyqtSignal(str, str)  # (hls_url, player_url)
            fail = pyqtSignal(str)
            def __init__(self, dl_url): super().__init__(); self.dl_url = dl_url
            def run(self):
                hls_url, player_url = get_hls_from_download_url(self.dl_url)
                if hls_url:
                    self.done.emit(hls_url, player_url or '')
                else:
                    self.fail.emit('無法取得 M3U8 串流 URL')

        self._fetcher = HlsFetcher(self.download_url)
        self._fetcher.done.connect(self._on_hls_ready)
        self._fetcher.fail.connect(self._on_error)
        self._fetcher.start()

    def _on_hls_ready(self, hls_url: str, player_url: str):
        self.status_label.setText('下載中...')
        self.worker = DownloadWorker(hls_url, self.output_path, referer=player_url)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.destination_signal.connect(self._on_destination)
        self.worker.start()

    def _on_progress(self, pct: float, speed: str):
        self.progress_bar.setValue(int(pct))
        self.status_label.setText(f'{pct:.1f}% — {speed}')

    def _on_destination(self, path: str):
        """當 yt-dlp 確定實際輸出路徑時更新標簽"""
        self.path_label.setText(f'→ {path}')

    def _on_finished(self, success: bool, message: str):
        if success:
            self.progress_bar.setValue(100)
            self.progress_bar.setStyleSheet("""
                QProgressBar { background:#3A3A3C; border-radius:3px; }
                QProgressBar::chunk { background:#0A84FF; border-radius:3px; }
            """)
            self.status_label.setText('✅ 完成')
            self.cancel_btn.setEnabled(False)
        else:
            # 自動重試：重新取得新 Token 再試一次
            if not getattr(self, '_retried', False):
                self._retried = True
                self.status_label.setText('Token 失效，重新取得中...')
                self.progress_bar.setValue(0)
                self.progress_bar.setStyleSheet("""
                    QProgressBar { background:#3A3A3C; border-radius:3px; }
                    QProgressBar::chunk { background:#FF9F0A; border-radius:3px; }
                """)

                class RetryFetcher(QThread):
                    done = pyqtSignal(str, str)
                    fail = pyqtSignal(str)
                    def __init__(self, dl_url): super().__init__(); self.dl_url = dl_url
                    def run(self):
                        hls_url, player_url = get_hls_from_download_url(self.dl_url)
                        if hls_url:
                            self.done.emit(hls_url, player_url or '')
                        else:
                            self.fail.emit('重試失敗：無法取得 M3U8 URL')

                self._retry_fetcher = RetryFetcher(self.download_url)
                self._retry_fetcher.done.connect(self._on_hls_ready)
                self._retry_fetcher.fail.connect(self._on_error)
                self._retry_fetcher.start()
            else:
                self.progress_bar.setStyleSheet("""
                    QProgressBar { background:#3A3A3C; border-radius:3px; }
                    QProgressBar::chunk { background:#FF3B30; border-radius:3px; }
                """)
                self.status_label.setText(f'❌ {message}')

    def _on_error(self, msg: str):
        self.status_label.setText(f'❌ {msg}')

    def cancel(self):
        """停止下載、刪除輸出檔（含 .part 暫存）並從佇列移除自己"""
        # 1. 停止工作執行緒
        for attr in ('worker', '_fetcher', '_retry_fetcher'):
            t = getattr(self, attr, None)
            if t is not None and hasattr(t, 'isRunning') and t.isRunning():
                t.terminate()

        # 2. 刪除已下載 / 未完成的檔案
        import os
        for ext in ('', '.part', '.ytdl'):
            p = self.output_path + ext
            try:
                if os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass

        # 3. 從佇列 layout 移除並刪除 widget
        if self.parent() is not None:
            layout = self.parent().layout()
            if layout is not None:
                layout.removeWidget(self)
        self.hide()
        self.deleteLater()


# ============================================================
# 下載管理器 Dialog
# ============================================================

class JavmixDownloadDialog(QDialog):
    def __init__(self, code: str = '', download_url: str = '', is_mosaic: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle('🎬 Javmix 下載管理器')
        self.resize(560, 520)
        self.setMinimumWidth(480)
        self.download_items = []

        self._init_ui()
        self._apply_style()

        # 若傳入初始任務，填入並自動執行
        if code and download_url:
            self._add_download_task(code, download_url, is_mosaic)

    def _apply_style(self):
        self.setStyleSheet("""
            QDialog { background-color: #1C1C1E; color: #E5E5EA; font-family: 微软雅黑; }
            QLabel { color: #E5E5EA; }
            QLineEdit {
                background: #2C2C2E; color: #E5E5EA;
                border: 1px solid #3A3A3C; border-radius: 6px; padding: 6px 10px;
            }
            QPushButton {
                background: #0A84FF; color: white;
                border: none; border-radius: 6px;
                padding: 7px 16px; font-weight: bold;
            }
            QPushButton:hover { background: #007AFF; }
            QPushButton:disabled { background: #3A3A3C; color: #636366; }
            QScrollArea { border: none; }
        """)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        # 標題
        title = QLabel('📥 HLS 串流下載管理器')
        title.setStyleSheet('font-size: 16px; font-weight: bold; color: #FFFFFF; margin-bottom: 4px;')
        layout.addWidget(title)

        # 手動輸入區
        input_frame = QFrame()
        input_frame.setStyleSheet('QFrame { background:#2C2C2E; border-radius:8px; padding:8px; }')
        ifl = QVBoxLayout(input_frame)
        ifl.setSpacing(6)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel('番號:'))
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText('例如: DVMM-357')
        row1.addWidget(self.code_input, 1)
        ifl.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel('下載頁:'))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText('例如: https://iplayerhls.com/download/xxx_h')
        row2.addWidget(self.url_input, 1)
        ifl.addLayout(row2)

        row3 = QHBoxLayout()
        self.output_btn = QPushButton('儲存至...')
        self.output_btn.setStyleSheet('background:#3A3A3C; font-weight:normal;')
        self.output_btn.clicked.connect(self._choose_output)
        self.output_label = QLabel(str(Path.home() / 'Downloads'))
        self.output_label.setStyleSheet('color:#8E8E93; font-size:12px;')
        self.output_label.setWordWrap(True)
        self._output_dir = Path.home() / 'Downloads'
        row3.addWidget(self.output_btn)
        row3.addWidget(self.output_label, 1)
        ifl.addLayout(row3)

        add_btn = QPushButton('➕ 加入下載佇列')
        add_btn.clicked.connect(self._on_add_clicked)
        ifl.addWidget(add_btn)

        layout.addWidget(input_frame)

        # 下載佇列標題
        queue_hdr = QHBoxLayout()
        queue_lbl = QLabel('下載佇列')
        queue_lbl.setStyleSheet('font-weight: bold; color: #E5E5EA;')
        self.clear_done_btn = QPushButton('清除已完成')
        self.clear_done_btn.setStyleSheet('background:#3A3A3C; font-weight:normal; padding:4px 10px;')
        self.clear_done_btn.clicked.connect(self._clear_done)
        queue_hdr.addWidget(queue_lbl)
        queue_hdr.addStretch()
        queue_hdr.addWidget(self.clear_done_btn)
        layout.addLayout(queue_hdr)

        # 可捲動佇列區
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.queue_widget = QWidget()
        self.queue_layout = QVBoxLayout(self.queue_widget)
        self.queue_layout.setSpacing(6)
        self.queue_layout.addStretch()
        scroll.setWidget(self.queue_widget)
        layout.addWidget(scroll, 1)

        # 底部提示
        tip = QLabel('💡 下載由 yt-dlp 驅動，HLS 串流片段自動合併為 MP4')
        tip.setStyleSheet('color: #636366; font-size: 11px;')
        layout.addWidget(tip)

    def _choose_output(self):
        d = QFileDialog.getExistingDirectory(self, '選擇儲存資料夾', str(self._output_dir))
        if d:
            self._output_dir = Path(d)
            self.output_label.setText(d)

    def _on_add_clicked(self):
        code = self.code_input.text().strip().upper()
        url = self.url_input.text().strip()
        if not code or not url:
            QMessageBox.warning(self, '提示', '請填入番號和下載頁網址！')
            return
        self._add_download_task(code, url, is_mosaic=False)
        self.code_input.clear()
        self.url_input.clear()

    def _add_download_task(self, code: str, download_url: str, is_mosaic: bool = False):
        # Origin → CODE.mp4，Ai解碼 → MOSAIC-CODE.mp4
        filename = f'MOSAIC-{code}.mp4' if is_mosaic else f'{code}.mp4'
        out_path = str(self._output_dir / filename)

        item = DownloadItemWidget(code, download_url, out_path)
        item.cancel_clicked.connect(self._on_cancel)
        # 插入到 stretch 之前
        self.queue_layout.insertWidget(self.queue_layout.count() - 1, item)
        self.download_items.append(item)
        item.start_download()

    def _on_cancel(self, item: DownloadItemWidget):
        item.cancel()
        item.status_label.setText('已取消')

    def _clear_done(self):
        for item in list(self.download_items):
            if '完成' in item.status_label.text() or '取消' in item.status_label.text() or '❌' in item.status_label.text():
                self.queue_layout.removeWidget(item)
                item.deleteLater()
                self.download_items.remove(item)


# ============================================================
# 快速下載函式 (供外部呼叫)
# ============================================================

def open_downloader(code: str, download_url: str, is_mosaic: bool = False, parent=None):
    """從 LinkSearchDialog 呼叫此函式開啟下載管理器"""
    dlg = JavmixDownloadDialog(code=code, download_url=download_url, is_mosaic=is_mosaic, parent=parent)
    dlg.show()
    return dlg


if __name__ == '__main__':
    app = QApplication(sys.argv)
    dlg = JavmixDownloadDialog()
    dlg.show()
    sys.exit(app.exec())

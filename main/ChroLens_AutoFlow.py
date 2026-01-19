# -*- coding: utf-8 -*-
"""
AutoFlow - 智能影片自動分類工具
版本: 1.0.0
作者: Lucien
授權: GPL v3 + Commercial
"""

import sys
import os
import json
import re
import time
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                              QHBoxLayout, QPushButton, QLabel, QTextEdit, 
                              QProgressBar, QFileDialog, QFrame, QScrollArea,
                              QListWidget, QListWidgetItem, QSplitter, QDialog,
                              QCheckBox, QMessageBox, QInputDialog, QGridLayout, QSlider, QStackedWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QSettings, QPoint, QTimer, QUrl
from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap, QImage, QIcon, QCursor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
import requests
import cv2
import numpy as np

# 導入版本管理器和多視窗播放器
try:
    from version_manager import VersionManager
    from version_info_dialog import VersionInfoDialog
    from about import AboutDialog
    from multi_player import MultiPlayerWindow
except ImportError:
    VersionManager = None
    AboutDialog = None
    MultiPlayerWindow = None

VERSION = "1.0.0"
APP_NAME = "AutoFlow"
FULL_APP_NAME = "ChroLens_AutoFlow"
GITHUB_REPO = "Lucienwooo/ChroLens_AutoFlow"


class VideoProcessor(QThread):
    """影片處理執行緒"""
    progress_update = pyqtSignal(int, int, int, int)  # total, processed, skipped, failed
    log_update = pyqtSignal(str)
    current_file_update = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, folder_path, cache):
        super().__init__()
        self.folder_path = folder_path
        self.cache = cache
        self.is_running = True
    
    def run(self):
        """執行影片處理"""
        files = list(Path(self.folder_path).glob("*.mp4"))
        total = len(files)
        processed = 0
        skipped = 0
        failed = 0
        
        self.log_update.emit(f"找到 {total} 個影片檔案")
        
        # 先清理重複檔案
        files = self.remove_duplicate_files(files)
        total = len(files)
        self.log_update.emit(f"清理重複檔案後剩餘 {total} 個檔案")
        
        for i, file_path in enumerate(files):
            if not self.is_running:
                break
                
            self.current_file_update.emit(f"正在處理: {file_path.name}")
            
            code = self.extract_video_code(file_path.name)
            if not code:
                self.log_update.emit(f"[跳過] {file_path.name} - 無法提取番號")
                skipped += 1
                self.progress_update.emit(total, processed, skipped, failed)
                continue
            
            self.log_update.emit(f"[{i+1}/{total}] {file_path.name}")
            self.log_update.emit(f"  番號: {code}")
            
            if code in self.cache:
                actress = self.cache[code]
                self.log_update.emit(f"  [快取] {actress}")
            else:
                actress = self.search_actress(code)
                if actress:
                    self.cache[code] = actress
                else:
                    self.log_update.emit(f"  [失敗] 搜尋失敗")
                    failed += 1
                    self.progress_update.emit(total, processed, skipped, failed)
                    continue
                
                time.sleep(2)
            
            if actress in ["UNKNOWN", "MULTIPLE"]:
                self.log_update.emit(f"  [跳過] {actress}")
                skipped += 1
                self.progress_update.emit(total, processed, skipped, failed)
                continue
            
            if self.move_video_file(file_path, actress):
                self.log_update.emit(f"  [完成] -> {actress}\\")
                processed += 1
            else:
                skipped += 1
            
            self.progress_update.emit(total, processed, skipped, failed)
            
            if (i + 1) % 5 == 0:
                self.save_cache()
        
        self.save_cache()
        self.log_update.emit("=== 處理完成 ===")
        self.finished.emit()
    
    def remove_duplicate_files(self, files):
        """移除重複檔案"""
        files_to_keep = []
        files_to_remove = []
        
        file_groups = {}
        
        for file_path in files:
            stem = file_path.stem
            base_name = re.sub(r'\s*\(\d+\)$', '', stem)
            group_key = re.sub(r'^(A-)?MOSAIC-ARCHIVE-', '', base_name, flags=re.IGNORECASE)
            group_key = re.sub(r'^ARCHIVE-MOSAIC-', '', group_key, flags=re.IGNORECASE)
            group_key = group_key.upper()
            
            if group_key not in file_groups:
                file_groups[group_key] = []
            
            file_groups[group_key].append({
                'path': file_path,
                'stem': stem,
                'base_name': base_name,
                'has_number_suffix': bool(re.search(r'\(\d+\)$', stem)),
                'has_mosaic_prefix': bool(re.match(r'^(A-)?MOSAIC-ARCHIVE-', stem, re.IGNORECASE))
            })
        
        for group_key, group_files in file_groups.items():
            if len(group_files) == 1:
                files_to_keep.append(group_files[0]['path'])
            else:
                no_suffix_files = [f for f in group_files if not f['has_number_suffix']]
                
                if no_suffix_files:
                    mosaic_files = [f for f in no_suffix_files if f['has_mosaic_prefix']]
                    
                    if mosaic_files:
                        files_to_keep.append(mosaic_files[0]['path'])
                        for f in group_files:
                            if f['path'] != mosaic_files[0]['path']:
                                files_to_remove.append(f['path'])
                    else:
                        files_to_keep.append(no_suffix_files[0]['path'])
                        for f in group_files:
                            if f['path'] != no_suffix_files[0]['path']:
                                files_to_remove.append(f['path'])
                else:
                    files_to_keep.append(group_files[0]['path'])
                    for f in group_files[1:]:
                        files_to_remove.append(f['path'])
        
        for file_path in files_to_remove:
            try:
                file_path.unlink()
                self.log_update.emit(f"[清理] 已刪除重複檔案: {file_path.name}")
            except Exception as e:
                self.log_update.emit(f"[錯誤] 無法刪除 {file_path.name}: {e}")
        
        return files_to_keep
    
    def extract_video_code(self, filename):
        """提取影片番號"""
        name = Path(filename).stem
        name = re.sub(r'^(A-)?MOSAIC-ARCHIVE-', '', name, flags=re.IGNORECASE)
        name = re.sub(r'^ARCHIVE-MOSAIC-', '', name, flags=re.IGNORECASE)
        
        patterns = [
            r'([A-Z]+-\d+)',
            r'([A-Z]+\d+)',
            r'(FC2-PPV-\d+)',
            r'(FC2-\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, name, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        
        return None
    
    def search_actress(self, code):
        """搜尋女優名稱"""
        # 檢查是否為FC2影片
        if code.upper().startswith('FC2'):
            self.log_update.emit(f"  [FC2] 分類到FC2資料夾")
            return "FC2"
        
        self.log_update.emit(f"  搜尋中...")
        
        try:
            url = f"https://av-wiki.net/{code}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                content = response.text
                
                # 簡單的女優名稱提取邏輯
                actress_match = re.search(r'<title>(.+?)</title>', content)
                if actress_match:
                    actress_name = actress_match.group(1).split('-')[0].strip()
                    self.log_update.emit(f"  [找到] {actress_name}")
                    return actress_name
            
            return "UNKNOWN"
            
        except Exception as e:
            self.log_update.emit(f"  [錯誤] {str(e)}")
            return None
    
    def move_video_file(self, file_path, actress_name):
        """移動影片檔案"""
        try:
            clean_name = actress_name.strip()
            for char in '<>:"/\\|?*':
                clean_name = clean_name.replace(char, '_')
            
            target_folder = Path(self.folder_path) / clean_name
            target_folder.mkdir(exist_ok=True)
            
            target_path = target_folder / file_path.name
            if target_path.exists():
                self.log_update.emit(f"  [跳過] 檔案已存在")
                return False
            
            file_path.rename(target_path)
            return True
            
        except Exception as e:
            self.log_update.emit(f"  [錯誤] {str(e)}")
            return False
    
    def save_cache(self):
        """儲存快取"""
        cache_file = Path.home() / "Downloads" / "actress_cache.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_update.emit(f"快取儲存失敗: {str(e)}")
    
    def stop(self):
        """停止處理"""
        self.is_running = False


class ClickableSlider(QSlider):
    """支援點擊直接跳轉的 Slider"""
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            val = self.minimum() + ((self.maximum() - self.minimum()) * event.position().x()) / self.width()
            self.setValue(int(val))
            self.sliderMoved.emit(self.value())
        super().mousePressEvent(event)


class VideoListItem(QWidget):
    """影片列表項目"""
    deleted = pyqtSignal(object)
    renamed = pyqtSignal(object)
    
    def __init__(self, video_path, is_dark=False, parent_window=None):
        super().__init__()
        self.video_path = video_path
        self.is_dark = is_dark
        self.parent_window = parent_window
        self.video_capture = None
        self.total_frames = 0
        self.fps = 0
        self.is_playing_inline = False
        
        # 媒體播放器組件
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        try:
            cap = cv2.VideoCapture(str(self.video_path))
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
        except:
            pass
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # 左側：縮圖和檔名
        left_layout = QVBoxLayout()
        left_layout.setSpacing(4)
        
        # 顯示區域疊加（縮圖 與 播放器）
        self.display_stack = QStackedWidget()
        self.display_stack.setFixedSize(320, 180)
        
        # 縮圖
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(320, 180)
        bg_color = "#2C2C2E" if self.is_dark else "#E5E5EA"
        self.thumbnail_label.setStyleSheet(f"background-color: {bg_color}; border-radius: 6px;")
        self.thumbnail_label.setScaledContents(True)
        self.thumbnail_label.setMouseTracking(True)
        self.thumbnail_label.installEventFilter(self)
        
        # 內嵌播放器
        self.video_widget = QVideoWidget()
        self.video_widget.setFixedSize(320, 180)
        self.video_widget.installEventFilter(self) # 增加事件監聽
        self.media_player.setVideoOutput(self.video_widget)
        
        self.display_stack.addWidget(self.thumbnail_label)
        self.display_stack.addWidget(self.video_widget)
        
        self.load_thumbnail()
        
        # 播放進度條（取代原本的 QProgressBar 以支援點擊跳轉）
        self.progress_bar = ClickableSlider(Qt.Orientation.Horizontal)
        self.progress_bar.setFixedSize(320, 6)
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        progress_color = "#007AFF" if self.is_dark else "#0066CC"
        self.progress_bar.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: none;
                height: 4px;
                background: {bg_color};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {progress_color};
                width: 0px; 
                height: 0px;
            }}
            QSlider::sub-page:horizontal {{
                background: {progress_color};
                border-radius: 2px;
            }}
        """)
        self.progress_bar.sliderMoved.connect(self.seek_video)
        self.progress_bar.sliderPressed.connect(self.on_slider_pressed)
        self.progress_bar.sliderReleased.connect(self.on_slider_released)
        self.is_seeking = False
        
        # 檔名
        self.filename_label = QLabel(self.video_path.name)
        text_color = "#E5E5EA" if self.is_dark else "#1C1C1E"
        self.filename_label.setStyleSheet(f"font-size: 10px; color: {text_color};")
        self.filename_label.setWordWrap(True)
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.filename_label.setMaximumWidth(320)
        
        left_layout.addWidget(self.display_stack)
        left_layout.addWidget(self.progress_bar)
        left_layout.addWidget(self.filename_label)
        
        # 右側：按鈕群組
        button_layout = QVBoxLayout()
        button_layout.setSpacing(4)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        self.play_btn = QPushButton("▶️ 播放")
        self.play_btn.setFixedSize(60, 32)
        self.play_btn.setStyleSheet(self.get_button_style("#34C759"))
        self.play_btn.clicked.connect(self.toggle_inline_playback)
        
        self.rename_btn = QPushButton("✏️ 更名")
        self.rename_btn.setFixedSize(60, 32)
        self.rename_btn.setStyleSheet(self.get_button_style("#007AFF"))
        self.rename_btn.clicked.connect(self.rename_video)
        
        self.delete_btn = QPushButton("🗑️ 刪除")
        self.delete_btn.setFixedSize(60, 32)
        self.delete_btn.setStyleSheet(self.get_button_style("#FF3B30"))
        self.delete_btn.clicked.connect(self.delete_video)
        
        # 音量控制條 (移除圖示，寬度設為 60)
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(50)
        self.vol_slider.setFixedSize(60, 20) # 寬度與按鈕一致
        self.vol_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #3A3A3C;
                height: 4px;
                background: #3A3A3C;
                margin: 2px 0;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #8E8E93;
                border: 1px solid #8E8E93;
                width: 12px;
                height: 12px;
                margin: -5px 0;
                border-radius: 6px;
            }
        """)
        self.vol_slider.valueChanged.connect(self.update_volume)
        
        button_layout.addWidget(self.play_btn)
        button_layout.addWidget(self.rename_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addWidget(self.vol_slider) # 直接加入滑桿
        button_layout.addStretch()
        
        main_layout.addLayout(left_layout)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 連接播放器信號
        self.media_player.playbackStateChanged.connect(self.on_playback_state_changed)
        self.media_player.positionChanged.connect(self.update_video_position)
        self.media_player.durationChanged.connect(self.update_video_duration)
    
    def get_button_style(self, color):
        """獲取按鈕樣式"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}DD;
            }}
            QPushButton:pressed {{
                background-color: {color}AA;
            }}
        """
    
    def eventFilter(self, obj, event):
        """事件過濾器"""
        # 顯示區域點擊 (縮圖或影片畫面)
        if obj in [self.thumbnail_label, self.video_widget]:
            if event.type() == event.Type.MouseButtonPress:
                if event.button() == Qt.MouseButton.LeftButton:
                    self.toggle_inline_playback()
                    return True
                elif event.button() == Qt.MouseButton.RightButton:
                    self.open_video_external()
                    return True
        
        # 縮圖滑鼠移動預覽 (僅在縮圖顯示時)
        if obj == self.thumbnail_label:
            if event.type() == event.Type.MouseMove:
                pos = event.pos()
                width = self.thumbnail_label.width()
                progress = pos.x() / width
                progress = max(0.0, min(1.0, progress))
                
                self.progress_bar.setValue(int(progress * 1000)) # 使用新的 1000 範圍
                self.load_frame_at_progress(progress)
                return True
            
            elif event.type() == event.Type.Leave:
                self.load_thumbnail()
                self.progress_bar.setValue(0)
                return True
        
        return super().eventFilter(obj, event)
    
    def load_frame_at_progress(self, progress):
        """載入指定進度的畫面"""
        if self.total_frames == 0:
            return
        
        try:
            cap = cv2.VideoCapture(str(self.video_path))
            target_frame = int(self.total_frames * progress)
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                self.thumbnail_label.setPixmap(pixmap.scaled(320, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        except Exception as e:
            print(f"載入畫面失敗: {e}")
    
    def update_volume(self, value):
        """更新個別影片音量"""
        self.audio_output.setVolume(value / 100.0)

    def load_thumbnail(self):
        """載入縮圖"""
        try:
            cap = cv2.VideoCapture(str(self.video_path))
            cap.set(cv2.CAP_PROP_POS_MSEC, 5000)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qt_image = QImage(frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_image)
                self.thumbnail_label.setPixmap(pixmap.scaled(320, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        except:
            pass
    
    def update_video_position(self, position):
        """更新播放進度條位元"""
        if not self.is_seeking and self.media_player.duration() > 0:
            self.progress_bar.setValue(int(position * 1000 / self.media_player.duration()))

    def update_video_duration(self, duration):
        """更新影片總時長"""
        pass

    def seek_video(self, position):
        """拖曳進度條時跳轉"""
        if self.media_player.duration() > 0:
            self.media_player.setPosition(int(position * self.media_player.duration() / 1000))

    def on_slider_pressed(self):
        self.is_seeking = True

    def on_slider_released(self):
        self.is_seeking = False
        self.seek_video(self.progress_bar.value())

    def toggle_inline_playback(self):
        """切換內嵌播放與停止"""
        if not self.is_playing_inline:
            # 切換前確保 Widget 是顯示狀態
            self.video_widget.show()
            self.display_stack.setCurrentWidget(self.video_widget)
            
            # 設定來源並播放
            self.media_player.setSource(QUrl.fromLocalFile(str(self.video_path)))
            self.media_player.play()
            self.is_playing_inline = True
            
            # 更新按鈕樣式
            self.play_btn.setText("⏸️ 暫停")
            self.play_btn.setStyleSheet(self.get_button_style("#FF9500"))
        else:
            # 切換 暫停/播放
            if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.media_player.pause()
            else:
                self.media_player.play()

    def on_playback_state_changed(self, state):
        """處理播放狀態改變"""
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_btn.setText("⏸️ 暫停")
            self.is_playing_inline = True
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self.play_btn.setText("▶️ 繼續")
            self.is_playing_inline = True
        else:
            self.play_btn.setText("▶️ 播放")
            self.play_btn.setStyleSheet(self.get_button_style("#34C759"))
            self.display_stack.setCurrentWidget(self.thumbnail_label)
            self.is_playing_inline = False

    def open_video_external(self):
        """開啟外部播放器"""
        try:
            # 如果正在內嵌播放，先暫停/停止
            self.media_player.stop()
            os.startfile(str(self.video_path))
        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"無法開啟影片: {e}")
    
    def rename_video(self):
        """重命名影片"""
        current_name = self.video_path.stem
        new_name, ok = QInputDialog.getText(
            self,
            "重命名影片",
            "請輸入新的檔案名稱:",
            text=current_name
        )
        
        if ok and new_name and new_name != current_name:
            try:
                new_path = self.video_path.parent / f"{new_name}{self.video_path.suffix}"
                
                if new_path.exists():
                    QMessageBox.warning(self, "錯誤", "檔案名稱已存在!")
                    return
                
                self.video_path.rename(new_path)
                self.video_path = new_path
                self.filename_label.setText(new_path.name)
                self.renamed.emit(self)
            except Exception as e:
                QMessageBox.warning(self, "錯誤", f"重命名失敗: {e}")
    
    def delete_video(self):
        """刪除影片（不確認）"""
        try:
            self.video_path.unlink()
            self.deleted.emit(self)
        except Exception as e:
            QMessageBox.warning(self, "錯誤", f"刪除失敗: {e}")


class StatCard(QFrame):
    """統計卡片"""
    def __init__(self, title, color, is_dark=False):
        super().__init__()
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        bg_color = "#2C2C2E" if is_dark else "white"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(4)
        
        self.title_label = QLabel(title)
        title_color = "#98989D" if is_dark else "#8E8E93"
        self.title_label.setStyleSheet(f"color: {title_color}; font-size: 10px;")
        
        self.value_label = QLabel("0")
        self.value_label.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold;")
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        
        self.setLayout(layout)
    
    def set_value(self, value):
        """設置值"""
        self.value_label.setText(str(value))


class MainWindow(QMainWindow):
    """主視窗"""
    def __init__(self):
        super().__init__()
        self.cache = {}
        self.load_cache()
        self.processor = None
        self.selected_folder = ""
        
        self.settings = QSettings("Lucien", APP_NAME)
        self.is_dark = self.settings.value("dark_mode", True, type=bool)
        
        if VersionManager:
            self.version_manager = VersionManager(GITHUB_REPO, VERSION, logger=self.add_log)
        else:
            self.version_manager = None
        
        self.init_ui()
        self.apply_theme()
        
        if self.version_manager:
            self.check_updates_async()
    
    def check_updates_async(self):
        """異步檢查更新"""
        def check():
            time.sleep(2)
            update_info = self.version_manager.check_for_updates()
            if update_info:
                self.show_update_dialog(update_info)
        
        import threading
        threading.Thread(target=check, daemon=True).start()
    
    def show_update_dialog(self, update_info):
        """顯示更新對話框"""
        reply = QMessageBox.question(
            self,
            "發現新版本",
            f"發現新版本 {update_info['version']}!\n\n是否立即更新?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.download_and_install_update(update_info)
    
    def download_and_install_update(self, update_info):
        """下載並安裝更新"""
        zip_path = self.version_manager.download_update(update_info['download_url'])
        if zip_path:
            extract_dir = self.version_manager.extract_update(zip_path)
            if extract_dir:
                if self.version_manager.apply_update(extract_dir, restart_after=True):
                    QApplication.quit()
    
    def init_ui(self):
        """初始化UI"""
        self.setWindowTitle(f"🎬 {APP_NAME} v{VERSION}")
        self.setMinimumSize(1000, 650)
        self.resize(1400, 750)
        
        self.create_icon()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # 左側面板
        left_panel = QWidget()
        left_panel.setMinimumWidth(350)
        left_panel.setMaximumWidth(450)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        # 標題
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        
        title_row = QHBoxLayout()
        title = QLabel(f"🎬 {APP_NAME}")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title_row.addWidget(title)
        title_row.addStretch()
        
        self.theme_toggle = QCheckBox("🌙 深色模式")
        self.theme_toggle.setChecked(self.is_dark)
        self.theme_toggle.setStyleSheet("font-size: 10px;")
        self.theme_toggle.stateChanged.connect(self.toggle_theme)
        title_row.addWidget(self.theme_toggle)
        
        subtitle = QLabel(f"智能影片自動分類工具 v{VERSION}")
        subtitle.setStyleSheet("font-size: 10px;")
        
        header_layout.addLayout(title_row)
        header_layout.addWidget(subtitle)
        
        # 統計卡片
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(6)
        
        self.total_card = StatCard("總檔案數", "#007AFF", self.is_dark)
        self.processed_card = StatCard("已處理", "#34C759", self.is_dark)
        self.skipped_card = StatCard("已跳過", "#FF9500", self.is_dark)
        self.failed_card = StatCard("失敗", "#FF3B30", self.is_dark)
        
        stats_layout.addWidget(self.total_card)
        stats_layout.addWidget(self.processed_card)
        stats_layout.addWidget(self.skipped_card)
        stats_layout.addWidget(self.failed_card)
        
        # 進度
        self.progress_widget = QFrame()
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(4)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        
        progress_header = QHBoxLayout()
        self.progress_title = QLabel("處理進度")
        self.progress_title.setStyleSheet("font-size: 11px; font-weight: 600;")
        self.progress_percent = QLabel("0%")
        self.progress_percent.setStyleSheet("font-size: 11px; font-weight: 600; color: #007AFF;")
        progress_header.addWidget(self.progress_title)
        progress_header.addStretch()
        progress_header.addWidget(self.progress_percent)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        
        self.current_file_label = QLabel("未開始")
        self.current_file_label.setStyleSheet("font-size: 9px;")
        
        progress_layout.addLayout(progress_header)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.current_file_label)
        self.progress_widget.setLayout(progress_layout)
        
        # 日誌
        self.log_widget = QFrame()
        log_layout = QVBoxLayout()
        log_layout.setSpacing(4)
        log_layout.setContentsMargins(0, 0, 0, 0)
        
        log_header = QLabel("處理日誌")
        log_header.setStyleSheet("font-size: 11px; font-weight: 600;")
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        
        log_layout.addWidget(log_header)
        log_layout.addWidget(self.log_text)
        self.log_widget.setLayout(log_layout)
        
        # 控制區
        control_layout = QVBoxLayout()
        control_layout.setSpacing(8)
        
        folder_layout = QHBoxLayout()
        folder_label = QLabel("📁 選擇資料夾")
        folder_label.setStyleSheet("font-size: 11px; font-weight: 600;")
        
        self.select_folder_btn = QPushButton("瀏覽...")
        self.select_folder_btn.setFixedHeight(28)
        self.select_folder_btn.clicked.connect(self.select_folder)
        
        folder_layout.addWidget(folder_label)
        folder_layout.addStretch()
        folder_layout.addWidget(self.select_folder_btn)
        
        self.folder_path_label = QLabel("未選擇")
        self.folder_path_label.setStyleSheet("font-size: 9px;")
        self.folder_path_label.setWordWrap(True)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(6)
        
        self.start_btn = QPushButton("▶️ 開始")
        self.start_btn.setFixedHeight(32)
        self.start_btn.clicked.connect(self.start_processing)
        
        self.stop_btn = QPushButton("⏸️ 停止")
        self.stop_btn.setFixedHeight(32)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_processing)
        
        self.player_btn = QPushButton("📺 多窗瀏覽")
        self.player_btn.setFixedHeight(32)
        self.player_btn.clicked.connect(self.show_multi_player)
        
        self.about_btn = QPushButton("ℹ️ 關於")
        self.about_btn.setFixedHeight(32)
        self.about_btn.clicked.connect(self.show_about)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        button_layout.addWidget(self.player_btn)
        button_layout.addWidget(self.about_btn)
        
        control_layout.addLayout(folder_layout)
        control_layout.addWidget(self.folder_path_label)
        control_layout.addLayout(button_layout)
        
        left_layout.addLayout(header_layout)
        left_layout.addLayout(stats_layout)
        left_layout.addWidget(self.progress_widget)
        left_layout.addWidget(self.log_widget, 1)
        left_layout.addLayout(control_layout)
        left_panel.setLayout(left_layout)
        
        # 右側面板 - 影片列表
        self.right_panel = QFrame()
        
        right_layout = QVBoxLayout()
        right_layout.setSpacing(4)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        list_header = QHBoxLayout()
        self.list_title = QLabel("影片列表")
        self.list_title.setStyleSheet("font-size: 11px; font-weight: 600;")
        
        self.list_hint = QLabel("滑鼠懸停即時預覽 | 點擊播放按鈕開啟影片")
        self.list_hint.setStyleSheet("font-size: 9px;")
        
        list_header.addWidget(self.list_title)
        list_header.addStretch()
        list_header.addWidget(self.list_hint)
        
        # 影片列表（網格佈局）
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.video_grid_widget = QWidget()
        self.video_grid_layout = QGridLayout()
        self.video_grid_layout.setSpacing(8)
        self.video_grid_layout.setContentsMargins(4, 4, 4, 4)
        self.video_grid_widget.setLayout(self.video_grid_layout)
        
        scroll_area.setWidget(self.video_grid_widget)
        
        right_layout.addLayout(list_header)
        right_layout.addWidget(scroll_area)
        self.right_panel.setLayout(right_layout)
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.right_panel, 1)
        
        central_widget.setLayout(main_layout)
        
        self.add_log(f"ChroLens_AutoFlow v{VERSION} 已啟動")
        self.add_log("已載入快取: {} 個條目".format(len(self.cache)))
    
    def create_icon(self):
        """創建圖標"""
        try:
            import sys
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, "icon.ico")
            else:
                icon_path = "icon.ico"
            
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except:
            pass
    
    def apply_theme(self):
        """應用主題"""
        if self.is_dark:
            self.setStyleSheet("""
                QMainWindow { background-color: #1C1C1E; }
                QWidget { color: #E5E5EA; }
                QLabel { color: #E5E5EA; }
                QCheckBox { color: #E5E5EA; }
            """)
            
            self.progress_widget.setStyleSheet("""
                QFrame {
                    background-color: #2C2C2E;
                    border-radius: 8px;
                    padding: 8px 12px;
                }
            """)
            
            self.log_widget.setStyleSheet("""
                QFrame {
                    background-color: #2C2C2E;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            
            self.right_panel.setStyleSheet("""
                QFrame {
                    background-color: #2C2C2E;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            
            self.log_text.setStyleSheet("""
                QTextEdit {
                    background-color: #1C1C1E;
                    color: #E5E5EA;
                    border: none;
                    border-radius: 4px;
                    padding: 6px;
                    font-family: Consolas;
                    font-size: 9px;
                }
            """)
            
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    background-color: #3A3A3C;
                    border-radius: 3px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #007AFF;
                    border-radius: 3px;
                }
            """)
        else:
            self.setStyleSheet("QMainWindow { background-color: #F5F5F7; }")
            
            self.progress_widget.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 8px;
                    padding: 8px 12px;
                }
            """)
            
            self.log_widget.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            
            self.right_panel.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            
            self.log_text.setStyleSheet("""
                QTextEdit {
                    background-color: #F5F5F7;
                    color: #3A3A3C;
                    border: none;
                    border-radius: 4px;
                    padding: 6px;
                    font-family: Consolas;
                    font-size: 9px;
                }
            """)
            
            self.progress_bar.setStyleSheet("""
                QProgressBar {
                    border: none;
                    background-color: #E5E5EA;
                    border-radius: 3px;
                    text-align: center;
                }
                QProgressBar::chunk {
                    background-color: #007AFF;
                    border-radius: 3px;
                }
            """)
    
    def toggle_theme(self):
        """切換主題"""
        self.is_dark = self.theme_toggle.isChecked()
        self.settings.setValue("dark_mode", self.is_dark)
        self.apply_theme()
        
        # 重新載入影片列表以應用新主題
        if self.selected_folder:
            self.load_video_list()
    
    def add_log(self, message):
        """添加日誌"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
    
    def update_progress(self, total, processed, skipped, failed):
        """更新進度"""
        self.total_card.set_value(total)
        self.processed_card.set_value(processed)
        self.skipped_card.set_value(skipped)
        self.failed_card.set_value(failed)
        
        if total > 0:
            percent = int((processed + skipped + failed) / total * 100)
            self.progress_bar.setValue(percent)
            self.progress_percent.setText(f"{percent}%")
    
    def update_current_file(self, filename):
        """更新當前處理檔案"""
        self.current_file_label.setText(filename)
    
    def load_cache(self):
        """載入快取"""
        cache_file = Path.home() / "Downloads" / "actress_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                    self.cache = {k: v for k, v in self.cache.items() if v != "如果系統沒有"}
            except Exception as e:
                print(f"快取載入失敗: {e}")
    
    def select_folder(self):
        """選擇資料夾"""
        folder = QFileDialog.getExistingDirectory(self, "選擇影片資料夾")
        if folder:
            self.selected_folder = folder
            self.folder_path_label.setText(folder)
            self.add_log(f"已選擇資料夾: {folder}")
            self.load_video_list()
    
    def load_video_list(self):
        """載入影片列表並顯示載入進度"""
        if not self.selected_folder:
            return
        
        # 初始化 UI 顯示載入狀態
        self.progress_title.setText("正在載入檔案與預覽...")
        self.current_file_label.setText("正在掃描影片...")
        self.progress_bar.setValue(0)
        self.progress_percent.setText("0%")
        QApplication.processEvents()

        files = list(Path(self.selected_folder).glob("*.mp4"))
        total_files = len(files)
        self.total_card.set_value(total_files)
        self.add_log(f"找到 {total_files} 個影片檔案碼，正在產生預覽...")
        
        # 清空現有網格
        for i in reversed(range(self.video_grid_layout.count())):
            widget = self.video_grid_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 顯示上限 (避免極大資料夾導致初始化過久)
        display_limit = 50
        files_to_load = files[:display_limit]
        load_count = len(files_to_load)
        
        # 以兩欄方式添加影片，並更新進度
        for index, file_path in enumerate(files_to_load):
            # 更新進度條
            percent = int((index + 1) / load_count * 1000) # 使用 0-1000 的範圍
            self.progress_bar.setValue(percent)
            self.progress_percent.setText(f"{int(percent/10)}%")
            self.current_file_label.setText(f"載入中 ({index+1}/{load_count}): {file_path.name}")
            
            # 強制 UI 更新，防止假死
            QApplication.processEvents()
            
            widget = VideoListItem(file_path, self.is_dark, self)
            widget.deleted.connect(lambda w=widget: self.on_video_deleted_grid(w))
            widget.renamed.connect(lambda w=widget: self.on_video_renamed(w))
            
            row = index // 2
            col = index % 2
            self.video_grid_layout.addWidget(widget, row, col)

        # 恢復 UI 狀態
        self.progress_title.setText("處理進度")
        self.current_file_label.setText(f"已成功載入 {load_count} 個影片預覽")
        self.add_log(f"共載入 {load_count} 個影片預覽")
    
    def on_video_deleted_grid(self, widget):
        """處理網格中的影片刪除"""
        self.video_grid_layout.removeWidget(widget)
        widget.deleteLater()
        self.add_log(f"已刪除影片: {widget.video_path.name}")
    
    def on_video_renamed(self, widget):
        """處理影片重命名"""
        self.add_log(f"已重命名影片: {widget.video_path.name}")
    
    def start_processing(self):
        """開始處理"""
        if not self.selected_folder:
            QMessageBox.warning(self, "警告", "請先選擇影片資料夾!")
            return
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.processor = VideoProcessor(self.selected_folder, self.cache)
        self.processor.progress_update.connect(self.update_progress)
        self.processor.log_update.connect(self.add_log)
        self.processor.current_file_update.connect(self.update_current_file)
        self.processor.finished.connect(self.on_processing_finished)
        self.processor.start()
        
        self.add_log("開始處理影片...")
    
    def stop_processing(self):
        """停止處理"""
        if self.processor:
            self.processor.stop()
            self.add_log("正在停止...")
    
    def on_processing_finished(self):
        """處理完成"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.add_log("處理已完成!")
        
        # 重新載入影片列表
        if self.selected_folder:
            self.load_video_list()
    
    def export_results(self):
        """匯出結果"""
        if not self.cache:
            QMessageBox.information(self, "提示", "沒有可匯出的資料!")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "匯出結果",
            "actress_mapping.csv",
            "CSV Files (*.csv)"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8-sig') as f:
                    f.write("Video Code,Actress Name\n")
                    for code, actress in self.cache.items():
                        f.write(f"{code},{actress}\n")
                self.add_log(f"[成功] 已匯出到: {filename}")
            except Exception as e:
                self.add_log(f"[錯誤] 匯出失敗: {str(e)}")
    
    def show_multi_player(self):
        """顯示多視窗播放器"""
        if not self.selected_folder:
            QMessageBox.warning(self, "提示", "請先選擇影片資料夾!")
            return
        
        files = list(Path(self.selected_folder).glob("*.mp4"))
        if not files:
            QMessageBox.warning(self, "提示", "資料夾中沒有影片檔案!")
            return
        
        if MultiPlayerWindow:
            player = MultiPlayerWindow(files, self.is_dark, self)
            player.show()
            self.add_log(f"已開啟多視窗播放器，共 {len(files)} 個影片")
        else:
            QMessageBox.warning(self, "錯誤", "無法載入多視窗播放器模組!")
    
    def show_about(self):
        """顯示關於"""
        if VersionInfoDialog and self.version_manager:
            dialog = VersionInfoDialog(self, self.version_manager, VERSION, FULL_APP_NAME)
            dialog.exec()
        elif AboutDialog:
            dialog = AboutDialog(self)
            dialog.exec()
        else:
            QMessageBox.about(
                self,
                f"關於 {FULL_APP_NAME}",
                f"{FULL_APP_NAME} v{VERSION}\n\n智能影片自動分類工具\n\n作者: Lucien\n授權: GPL v3 + Commercial"
            )


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    font = QFont("Segoe UI", 9)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

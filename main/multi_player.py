# -*- coding: utf-8 -*-
"""
多視窗播放器模組 - 9宮格播放器 (增強版)
"""

import os
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QListWidget, QFrame, QSlider, 
                             QGridLayout, QScrollArea)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl, QMimeData
from PyQt6.QtGui import QPixmap, QImage, QDrag, QFontMetrics
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

class ElidedLabel(QLabel):
    """支援自動省略過長文字的標籤"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self._full_text = text

    def setText(self, text):
        self._full_text = text
        self.update_elision()

    def update_elision(self):
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width())
        super().setText(elided, is_full=False)

    def setText(self, text, is_full=True):
        if is_full:
            self._full_text = text
        metrics = QFontMetrics(self.font())
        elided = metrics.elidedText(self._full_text, Qt.TextElideMode.ElideRight, self.width())
        super().setText(elided)

    def resizeEvent(self, event):
        self.update_elision()
        super().resizeEvent(event)

class ClickableSlider(QSlider):
    """支援點擊直接跳轉的 Slider"""
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            val = self.minimum() + ((self.maximum() - self.minimum()) * event.pos().x()) / self.width()
            self.setValue(int(val))
            self.sliderMoved.emit(self.value())
        super().mousePressEvent(event)

class DraggableListWidget(QListWidget):
    """自定義可拖放列表，確保 MIME 數據包含文字"""
    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(item.text())
            drag.setMimeData(mime_data)
            drag.exec(supportedActions)

class MultiPlayerWindow(QDialog):
    def __init__(self, video_files, is_dark=True, parent=None):
        super().__init__(parent)
        self.video_files = video_files
        self.is_dark = is_dark
        self.player_widgets = []
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle("🎬 多視窗播放器 (9宮格)")
        self.resize(1800, 950)
        
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        left_panel = QWidget()
        left_panel.setFixedWidth(280)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        list_label = QLabel("影片列表 (拖曳至右側)")
        list_label.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {'white' if self.is_dark else 'black'};")
        
        self.video_list = DraggableListWidget()
        self.video_list.setDragEnabled(True)
        self.video_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {'#2C2C2E' if self.is_dark else '#F0F0F0'};
                border-radius: 6px;
                color: {'white' if self.is_dark else 'black'};
            }}
        """)
        
        for video_file in self.video_files:
            self.video_list.addItem(video_file.name)
        
        left_layout.addWidget(list_label)
        left_layout.addWidget(self.video_list)
        left_panel.setLayout(left_layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        grid_container = QWidget()
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(6)
        
        for i in range(9):
            player_widget = VideoPlayerWidget(i, self.is_dark)
            player_widget.video_dropped.connect(self.on_video_dropped)
            grid_layout.addWidget(player_widget, i // 3, i % 3)
            self.player_widgets.append(player_widget)
            
        scroll.setWidget(grid_container)
        
        main_layout.addWidget(left_panel)
        main_layout.addWidget(scroll, 1)
        self.setLayout(main_layout)
    
    def on_video_dropped(self, player_index, video_name):
        for video_file in self.video_files:
            if video_file.name == video_name:
                self.player_widgets[player_index].load_video(video_file)
                break

    def closeEvent(self, event):
        for player in self.player_widgets:
            player.media_player.stop()
        super().closeEvent(event)

class VideoPlayerWidget(QFrame):
    video_dropped = pyqtSignal(int, str)
    
    def __init__(self, index, is_dark=True):
        super().__init__()
        self.index = index
        self.is_dark = is_dark
        self.video_path = None
        self.setFixedSize(540, 380) 
        self.setAcceptDrops(True)
        
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_container = QFrame()
        self.video_container.setStyleSheet(f"background-color: black; border-radius: 4px;")
        v_layout = QVBoxLayout(self.video_container)
        v_layout.setContentsMargins(0, 0, 0, 0)
        
        self.info_label = QLabel(f"播放器 {self.index + 1}\n(右鍵清除)")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("color: #555; font-size: 12px;")
        v_layout.addWidget(self.info_label)
        
        self.video_widget = QVideoWidget()
        self.video_widget.hide()
        self.video_widget.installEventFilter(self)
        v_layout.addWidget(self.video_widget)
        self.media_player.setVideoOutput(self.video_widget)
        
        controls = QFrame()
        controls.setFixedHeight(40)
        c_layout = QHBoxLayout(controls)
        c_layout.setContentsMargins(8, 0, 8, 0)
        c_layout.setSpacing(10)
        
        self.play_btn = QPushButton("▶️")
        self.play_btn.setFixedSize(30, 30)
        self.play_btn.clicked.connect(self.toggle)
        
        self.seek_slider = ClickableSlider(Qt.Orientation.Horizontal)
        self.seek_slider.setRange(0, 1000)
        self.seek_slider.setFixedHeight(12)
        # 設定最小寬度為總寬度的約一半 (250px)
        self.seek_slider.setMinimumWidth(250)
        self.seek_slider.setStyleSheet("""
            QSlider::groove:horizontal { border: 1px solid #333; height: 4px; background: #444; border-radius: 2px; }
            QSlider::handle:horizontal { background: #007AFF; width: 10px; height: 10px; margin: -4px 0; border-radius: 5px; }
        """)
        self.seek_slider.sliderMoved.connect(self.set_position)
        self.seek_slider.sliderPressed.connect(self.on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self.on_seek_released)
        
        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(50)
        self.vol_slider.setFixedWidth(60)
        self.vol_slider.valueChanged.connect(lambda v: self.audio_output.setVolume(v/100.0))
        
        self.name_label = ElidedLabel("等待拖曳")
        self.name_label.setStyleSheet("font-size: 9px; color: gray;")
        
        c_layout.addWidget(self.play_btn)
        c_layout.addWidget(self.seek_slider, 2) # 進度條優先權較高
        c_layout.addWidget(self.vol_slider)
        c_layout.addWidget(self.name_label, 1) # 剩下的給檔名
        
        layout.addWidget(self.video_container)
        layout.addWidget(controls)
        
        self.media_player.positionChanged.connect(self.update_position)
        self.is_seeking = False

    def eventFilter(self, obj, event):
        if obj == self.video_widget and event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                self.toggle()
                return True
            elif event.button() == Qt.MouseButton.RightButton:
                self.clear_video()
                return True
        return super().eventFilter(obj, event)

    def clear_video(self):
        """清除當前載入的影片"""
        self.media_player.stop()
        self.media_player.setSource(QUrl(""))
        self.video_widget.hide()
        self.info_label.show()
        self.name_label.setText("等待拖曳")
        self.play_btn.setText("▶️")
        self.video_path = None
        self.seek_slider.setValue(0)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.video_container.setStyleSheet("border: 2px solid #007AFF;")

    def dragLeaveEvent(self, event):
        self.video_container.setStyleSheet("border: none;")

    def dropEvent(self, event):
        name = event.mimeData().text()
        self.video_dropped.emit(self.index, name)
        self.video_container.setStyleSheet("border: none;")

    def load_video(self, path):
        # 如果已經有影片正在播放，這會自動覆蓋
        self.video_path = path
        self.name_label.setText(path.name)
        self.info_label.hide()
        self.video_widget.show()
        self.media_player.setSource(QUrl.fromLocalFile(str(path)))
        self.media_player.play()
        self.play_btn.setText("⏸️")

    def toggle(self):
        if not self.video_path: return
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.play_btn.setText("▶️")
        else:
            self.media_player.play()
            self.play_btn.setText("⏸️")

    def update_position(self, position):
        if not self.is_seeking and self.media_player.duration() > 0:
            self.seek_slider.setValue(int(position * 1000 / self.media_player.duration()))

    def set_position(self, position):
        if self.media_player.duration() > 0:
            self.media_player.setPosition(int(position * self.media_player.duration() / 1000))

    def on_seek_pressed(self): self.is_seeking = True
    def on_seek_released(self):
        self.is_seeking = False
        self.set_position(self.seek_slider.value())

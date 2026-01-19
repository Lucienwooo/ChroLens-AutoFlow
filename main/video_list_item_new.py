# 新的 VideoListItem 類別 - 包含即時預覽、更名、刪除功能
# 請將此代碼替換原有的 VideoListItem 類別 (約在 212-270 行)

class VideoListItem(QWidget):
    deleted = pyqtSignal(object)  # 刪除信號
    renamed = pyqtSignal(object)  # 重命名信號
    
    def __init__(self, video_path, is_dark=False, parent_window=None):
        super().__init__()
        self.video_path = video_path
        self.is_dark = is_dark
        self.parent_window = parent_window
        self.video_capture = None
        self.total_frames = 0
        self.fps = 0
        
        # 初始化影片資訊
        try:
            cap = cv2.VideoCapture(str(self.video_path))
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            self.fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
        except:
            pass
        
        # 主佈局
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)
        
        # 左側:縮圖和檔名
        left_layout = QVBoxLayout()
        left_layout.setSpacing(6)
        
        # 縮圖 - 啟用滑鼠追蹤以實現即時預覽
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(320, 180)
        bg_color = "#2C2C2E" if is_dark else "#E5E5EA"
        self.thumbnail_label.setStyleSheet(f"background-color: {bg_color}; border-radius: 6px;")
        self.thumbnail_label.setScaledContents(True)
        self.thumbnail_label.setMouseTracking(True)  # 啟用滑鼠追蹤
        self.thumbnail_label.installEventFilter(self)  # 安裝事件過濾器
        
        # 載入初始縮圖
        self.load_thumbnail()
        
        # 檔名
        self.filename_label = QLabel(video_path.name)
        text_color = "#E5E5EA" if is_dark else "#1C1C1E"
        self.filename_label.setStyleSheet(f"font-size: 11px; color: {text_color};")
        self.filename_label.setWordWrap(True)
        self.filename_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        left_layout.addWidget(self.thumbnail_label)
        left_layout.addWidget(self.filename_label)
        
        # 右側:按鈕
        button_layout = QVBoxLayout()
        button_layout.setSpacing(6)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 更名按鈕
        self.rename_btn = QPushButton("✏️ 更名")
        self.rename_btn.setFixedSize(70, 28)
        self.rename_btn.setStyleSheet(self.get_button_style("#007AFF"))
        self.rename_btn.clicked.connect(self.rename_video)
        
        # 刪除按鈕
        self.delete_btn = QPushButton("🗑️ 刪除")
        self.delete_btn.setFixedSize(70, 28)
        self.delete_btn.setStyleSheet(self.get_button_style("#FF3B30"))
        self.delete_btn.clicked.connect(self.delete_video)
        
        # 開啟按鈕
        self.open_btn = QPushButton("▶️ 播放")
        self.open_btn.setFixedSize(70, 28)
        self.open_btn.setStyleSheet(self.get_button_style("#34C759"))
        self.open_btn.clicked.connect(self.open_video)
        
        button_layout.addWidget(self.open_btn)
        button_layout.addWidget(self.rename_btn)
        button_layout.addWidget(self.delete_btn)
        button_layout.addStretch()
        
        main_layout.addLayout(left_layout)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def get_button_style(self, color):
        """獲取按鈕樣式"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 10px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                opacity: 0.8;
            }}
        """
    
    def eventFilter(self, obj, event):
        """事件過濾器 - 實現滑鼠懸停即時預覽"""
        if obj == self.thumbnail_label:
            if event.type() == event.Type.MouseMove:
                # 獲取滑鼠在縮圖上的位置
                pos = event.pos()
                width = self.thumbnail_label.width()
                
                # 計算進度百分比
                progress = pos.x() / width
                progress = max(0.0, min(1.0, progress))  # 限制在 0-1 之間
                
                # 載入對應進度的畫面
                self.load_frame_at_progress(progress)
                return True
            
            elif event.type() == event.Type.Leave:
                # 滑鼠離開時恢復初始縮圖
                self.load_thumbnail()
                return True
        
        return super().eventFilter(obj, event)
    
    def load_frame_at_progress(self, progress):
        """載入指定進度的影片畫面"""
        if self.total_frames == 0:
            return
        
        try:
            cap = cv2.VideoCapture(str(self.video_path))
            
            # 計算目標幀數
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
    
    def load_thumbnail(self):
        """載入初始縮圖 (第5秒)"""
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
    
    def open_video(self):
        """開啟影片"""
        try:
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
                
                QMessageBox.information(self, "成功", "影片已重命名!")
            except Exception as e:
                QMessageBox.warning(self, "錯誤", f"重命名失敗: {e}")
    
    def delete_video(self):
        """刪除影片"""
        reply = QMessageBox.question(
            self,
            "確認刪除",
            f"確定要刪除影片嗎?\n\n{self.video_path.name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.video_path.unlink()  # 刪除檔案
                self.deleted.emit(self)
                QMessageBox.information(self, "成功", "影片已刪除!")
            except Exception as e:
                QMessageBox.warning(self, "錯誤", f"刪除失敗: {e}")

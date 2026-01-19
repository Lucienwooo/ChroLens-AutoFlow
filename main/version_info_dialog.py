# -*- coding: utf-8 -*-
"""
版本資訊與更新對話框 - ChroLens_AutoFlow
採用 ChroLens_Mimic 風格佈局
"""

import os
import sys
import threading
import time
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QProgressBar, QFrame,
                             QScrollArea, QApplication, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QMetaObject, Q_ARG, QSize
from PyQt6.QtGui import QFont, QColor, QIcon

class VersionInfoDialog(QDialog):
    """合併 Mimic 風格的版本資訊與更新對話框"""
    check_finished = pyqtSignal(object)
    update_state_signal = pyqtSignal(str, int)
    update_progress_signal = pyqtSignal(int, str)
    update_error = pyqtSignal(str)
    update_success = pyqtSignal()
    
    def __init__(self, parent, version_manager, current_version, app_name="ChroLens_AutoFlow"):
        super().__init__(parent)
        self.vm = version_manager
        self.current_version = current_version
        self.app_name = app_name
        self.update_info = None
        
        # 連接信號
        self.check_finished.connect(self._handle_check_result)
        self.update_state_signal.connect(self._update_ui_state)
        self.update_progress_signal.connect(self._update_prog_bar)
        self.update_error.connect(self._show_error)
        self.update_success.connect(self._show_success_msg)
        
        self.setWindowTitle(f"版本資訊 - {app_name}")
        self.setMinimumSize(550, 650)
        self.resize(550, 700)
        
        # 鎖定深色模式樣式
        self.setStyleSheet("""
            QDialog { background-color: #1C1C1E; }
            QWidget { color: #E5E5EA; font-family: 'LINESeedTW_TTF_Rg'; }
            QFrame#SectionFrame { 
                background-color: #2C2C2E; 
                border-radius: 10px; 
                border: 1px solid #3A3A3C;
            }
            QLabel#Header { font-size: 22px; font-weight: bold; color: #007AFF; }
            QLabel#SubHeader { font-size: 14px; font-weight: bold; color: #8E8E93; }
            QLabel#LabelNormal { font-size: 12px; color: #E5E5EA; }
            QLabel#LabelDim { font-size: 12px; color: #8E8E93; }
            QTextEdit { 
                background-color: #1C1C1E; 
                border: 1px solid #3A3A3C; 
                border-radius: 6px; 
                color: #E5E5EA; 
                font-size: 11px;
            }
        """)

        self.init_ui()
        
        # 設置圖示
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "pic", "umi_粉紅色.ico")
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except:
            pass
        
        # 背景檢查更新
        self.start_check()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # ========== 1. 頂部標題與關於區域 ==========
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel(self.app_name)
        title_label.setObjectName("Header")
        header_layout.addWidget(title_label)
        
        subtitle = QLabel("智能影片自動分類與多窗瀏覽工具")
        subtitle.setObjectName("LabelDim")
        header_layout.addWidget(subtitle)
        
        main_layout.addWidget(header_frame)
        
        # 關於欄位 (新增)
        about_frame = QFrame()
        about_frame.setObjectName("SectionFrame")
        about_layout = QVBoxLayout(about_frame)
        
        about_title = QLabel("關於本軟體")
        about_title.setObjectName("SubHeader")
        about_layout.addWidget(about_title)
        
        about_content = QLabel(
            "作者：Lucien\n"
            "授權：GPL v3 + Commercial License\n"
            "Discord：ChroLens Studio 社群\n"
            "GitHub：Lucienwooo/ChroLens_AutoFlow"
        )
        about_content.setObjectName("LabelNormal")
        about_content.setWordWrap(True)
        about_layout.addWidget(about_content)
        main_layout.addWidget(about_frame)
        
        # ========== 2. 版本狀態區域 ==========
        info_frame = QFrame()
        info_frame.setObjectName("SectionFrame")
        info_layout = QVBoxLayout(info_frame)
        
        info_title = QLabel("版本資訊")
        info_title.setObjectName("SubHeader")
        info_layout.addWidget(info_title)
        
        grid_layout = QVBoxLayout()
        grid_layout.setSpacing(8)
        
        # 目前版本
        curr_row = QHBoxLayout()
        curr_label = QLabel("目前版本：")
        curr_label.setObjectName("LabelNormal")
        curr_label.setFixedWidth(80)
        self.curr_val = QLabel(f"v{self.current_version}")
        self.curr_val.setStyleSheet("font-weight: bold; color: #007AFF;")
        curr_row.addWidget(curr_label)
        curr_row.addWidget(self.curr_val)
        curr_row.addStretch()
        grid_layout.addLayout(curr_row)
        
        # 最新版本
        new_row = QHBoxLayout()
        new_label = QLabel("最新版本：")
        new_label.setObjectName("LabelNormal")
        new_label.setFixedWidth(80)
        self.new_val = QLabel("檢查中...")
        self.new_val.setObjectName("LabelDim")
        new_row.addWidget(new_label)
        new_row.addWidget(self.new_val)
        new_row.addStretch()
        grid_layout.addLayout(new_row)
        
        # 更新狀態
        stat_row = QHBoxLayout()
        stat_label = QLabel("更新狀態：")
        stat_label.setObjectName("LabelNormal")
        stat_label.setFixedWidth(80)
        self.stat_val = QLabel("正在連線...")
        self.stat_val.setObjectName("LabelDim")
        stat_row.addWidget(stat_label)
        stat_row.addWidget(self.stat_val)
        stat_row.addStretch()
        grid_layout.addLayout(stat_row)
        
        info_layout.addLayout(grid_layout)
        main_layout.addWidget(info_frame)
        
        # ========== 3. 更新日誌區域 ==========
        notes_frame = QFrame()
        notes_frame.setObjectName("SectionFrame")
        notes_layout = QVBoxLayout(notes_frame)
        
        notes_title = QLabel("更新說明")
        notes_title.setObjectName("SubHeader")
        notes_layout.addWidget(notes_title)
        
        self.notes_text = QTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setPlaceholderText("正在從 GitHub 獲取更新日誌...")
        notes_layout.addWidget(self.notes_text)
        
        main_layout.addWidget(notes_frame)
        
        # ========== 4. 進度區域 (初始隱藏) ==========
        self.progress_container = QFrame()
        self.progress_container.setObjectName("SectionFrame")
        self.progress_container.hide()
        prog_layout = QVBoxLayout(self.progress_container)
        
        self.prog_label = QLabel("準備下載...")
        self.prog_label.setObjectName("LabelNormal")
        prog_layout.addWidget(self.prog_label)
        
        self.prog_bar = QProgressBar()
        self.prog_bar.setFixedHeight(8)
        self.prog_bar.setRange(0, 100)
        self.prog_bar.setValue(0)
        self.prog_bar.setTextVisible(False)
        self.prog_bar.setStyleSheet("""
            QProgressBar { background-color: #1C1C1E; border: none; border-radius: 4px; }
            QProgressBar::chunk { background-color: #34C759; border-radius: 4px; }
        """)
        prog_layout.addWidget(self.prog_bar)
        
        self.prog_detail = QLabel("")
        self.prog_detail.setObjectName("LabelDim")
        self.prog_detail.setAlignment(Qt.AlignmentFlag.AlignRight)
        prog_layout.addWidget(self.prog_detail)
        
        main_layout.addWidget(self.progress_container)
        
        # ========== 5. 按鈕區域 ==========
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.update_btn = QPushButton("立即更新")
        self.update_btn.setEnabled(False)
        self.update_btn.setFixedHeight(40)
        self.update_btn.setStyleSheet("""
            QPushButton { 
                background-color: #34C759; color: white; border-radius: 8px; font-weight: bold; font-size: 14px;
            }
            QPushButton:disabled { background-color: #3A3A3C; color: #8E8E93; }
            QPushButton:hover { background-color: #2FB34F; }
        """)
        self.update_btn.clicked.connect(self.start_update_process)
        
        self.close_btn = QPushButton("關閉")
        self.close_btn.setFixedHeight(40)
        self.close_btn.setStyleSheet("""
            QPushButton { 
                background-color: #3A3A3C; color: #E5E5EA; border-radius: 8px; font-size: 14px;
            }
            QPushButton:hover { background-color: #48484A; }
        """)
        self.close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(self.update_btn, 2)
        btn_layout.addWidget(self.close_btn, 1)
        main_layout.addLayout(btn_layout)

    def start_check(self):
        """啟動檢查更新線程"""
        threading.Thread(target=self._check_task, daemon=True).start()

    def _check_task(self):
        info = self.vm.check_for_updates()
        self.check_finished.emit(info)

    def _handle_check_result(self, info):
        if info:
            self.update_info = info
            self.new_val.setText(f"v{info['version']}")
            self.new_val.setStyleSheet("font-weight: bold; color: #34C759;")
            self.stat_val.setText("發現新版本可用！")
            self.stat_val.setStyleSheet("color: #34C759;")
            self.update_btn.setEnabled(True)
            self.notes_text.setPlainText(info['release_notes'])
        else:
            self.new_val.setText(f"v{self.current_version}")
            self.stat_val.setText("目前已是最新版本")
            self.stat_val.setStyleSheet("color: #8E8E93;")
            self.notes_text.setPlainText("您目前使用的是最新版本。\n無需進行任何更新項目。")

    def start_update_process(self):
        """開始更新流程"""
        if not self.update_info:
            return
            
        self.update_btn.setEnabled(False)
        self.progress_container.show()
        self.prog_label.setText("階段 1/3: 下載更新檔案")
        
        threading.Thread(target=self._update_task, daemon=True).start()

    def _update_task(self):
        """背景更新任務"""
        try:
            # 1. 下載
            zip_path = self.vm.download_update(self.update_info['download_url'], self._update_progress)
            if not zip_path: raise Exception("下載失敗")
            
            # 2. 解壓
            self.update_state_signal.emit("階段 2/3: 解壓縮檔案", 70)
            extract_dir = self.vm.extract_update(zip_path)
            if not extract_dir: raise Exception("解壓縮失敗")
            
            # 3. 準備套用 (Robocopy 腳本)
            self.update_state_signal.emit("階段 3/3: 安裝更新", 90)
            time.sleep(1)
            
            # 執行腳本
            success = self.vm.apply_update(extract_dir, restart_after=True)
            if success:
                self.update_state_signal.emit("✓ 更新完成！", 100)
                # 提示重啟
                self.update_success.emit()
            else:
                raise Exception("套用更新腳本失敗")
                
        except Exception as e:
            self.update_error.emit(str(e))

    def _update_progress(self, current, total):
        """下載進度回調"""
        if total > 0:
            percent = int((current / total) * 60) # 下載佔 60%
            detail = f"{current/(1024*1024):.1f}MB / {total/(1024*1024):.1f}MB"
            self.update_progress_signal.emit(percent, detail)

    def _update_prog_bar(self, val, detail):
        self.prog_bar.setValue(val)
        self.prog_detail.setText(detail)

    def _update_ui_state(self, label, val):
        self.prog_label.setText(label)
        self.prog_bar.setValue(val)
        self.prog_detail.setText("")

    def _show_success_msg(self):
        QMessageBox.information(self, "更新完成", "更新已準備就緒，程式將在點擊確定後自動重啟。")
        QApplication.quit()

    def _show_error(self, err):
        self.update_btn.setEnabled(True)
        self.prog_label.setText("✗ 更新失敗")
        self.prog_bar.setStyleSheet("QProgressBar::chunk { background-color: #FF3B30; }")
        QMessageBox.critical(self, "錯誤", f"更新過程中發生錯誤：\n\n{err}")

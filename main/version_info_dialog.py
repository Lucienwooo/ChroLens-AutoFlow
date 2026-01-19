# -*- coding: utf-8 -*-
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTextEdit, QProgressBar, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
import threading
import webbrowser

class VersionInfoDialog(QDialog):
    def __init__(self, parent, version_manager, current_version, app_name="ChroLens App"):
        super().__init__(parent)
        self.vm = version_manager
        self.current_version = current_version
        self.app_name = app_name
        
        self.setWindowTitle(f"關於 {app_name}")
        self.setFixedSize(450, 400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        title_label = QLabel(app_name)
        title_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        ver_label = QLabel(f"版本: {current_version}")
        ver_label.setStyleSheet("font-size: 14px; color: #8E8E93;")
        ver_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(ver_label)
        
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setHtml(f"<b>作者:</b> Lucien<br><b>授權:</b> GPL v3 + Commercial<br><br>專案首頁: <a href='https://github.com/{self.vm.github_repo}'>GitHub</a>")
        layout.addWidget(self.info_text)
        
        btn_layout = QHBoxLayout()
        self.check_btn = QPushButton("檢查更新")
        self.check_btn.clicked.connect(self.check_for_updates)
        btn_layout.addWidget(self.check_btn)
        
        close_btn = QPushButton("關閉")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
        
        self.status_label = QLabel("就緒")
        layout.addWidget(self.status_label)

    def check_for_updates(self):
        self.check_btn.setEnabled(False)
        self.status_label.setText("正在檢查更新...")
        
        def task():
            info = self.vm.check_for_updates()
            # 在 PyQt 中彈窗需要回到主線程
            from PyQt6.QtCore import QMetaObject, Q_ARG
            QMetaObject.invokeMethod(self, "_handle_result", Qt.ConnectionType.QueuedConnection, 
                                    Q_ARG(object, info))
            
        threading.Thread(target=task, daemon=True).start()

    def _handle_result(self, info):
        self.check_btn.setEnabled(True)
        if not info:
            self.status_label.setText("已是最新版本")
            QMessageBox.information(self, "更新", "目前已是最新版本！")
            return
            
        self.status_label.setText(f"發現新版本: {info['version']}")
        msg = f"發現新版本 {info['version']}！\\n\\n更新內容:\\n{info['release_notes']}\\n\\n是否立即更新？"
        reply = QMessageBox.question(self, "發現新版本", msg, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.download_and_update(info['download_url'])

    def download_and_update(self, url):
        self.status_label.setText("正在下載更新...")
        def dl_task():
            path = self.vm.download_update(url)
            if path:
                ext = self.vm.extract_update(path)
                if ext:
                    self.vm.apply_update(ext)
            else:
                QMetaObject.invokeMethod(self, "show_error", Qt.ConnectionType.QueuedConnection, Q_ARG(str, "下載失敗"))
        threading.Thread(target=dl_task, daemon=True).start()

    def show_error(self, err):
        QMessageBox.critical(self, "錯誤", err)

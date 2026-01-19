# -*- coding: utf-8 -*-
"""
關於對話框 - ChroLens_AutoFlow
"""

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt


class AboutDialog(QDialog):
    def __init__(self, parent=None, is_dark=False, version="1.0.0", app_name="ChroLens_AutoFlow"):
        super().__init__(parent)
        self.is_dark = is_dark
        self.setWindowTitle("關於")
        self.setFixedSize(450, 350)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # App icon and name
        title_layout = QHBoxLayout()
        title_label = QLabel(f"🎬 {app_name}")
        title_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {'#FFFFFF' if is_dark else '#1C1C1E'};")
        title_layout.addStretch()
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Version
        version_label = QLabel(f"版本 {version}")
        version_label.setStyleSheet(f"font-size: 14px; color: {'#8E8E93' if not is_dark else '#98989D'};")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Description
        desc_label = QLabel("ChroLens 系列 - 智能影片自動分類工具\n使用 AI 技術自動搜尋並分類影片")
        desc_label.setStyleSheet(f"font-size: 12px; color: {'#3A3A3C' if not is_dark else '#E5E5EA'}; line-height: 1.5;")
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        
        # Features
        features_label = QLabel(
            "✨ 特色功能\n\n"
            "• 自動搜尋女優名稱 (av-wiki.net)\n"
            "• 智能快取系統\n"
            "• 影片縮圖預覽 (OpenCV)\n"
            "• 批次處理\n"
            "• 深色/淺色主題\n"
            "• 自動更新功能"
        )
        features_label.setStyleSheet(f"font-size: 11px; color: {'#3A3A3C' if not is_dark else '#E5E5EA'}; line-height: 1.6;")
        
        # License
        license_label = QLabel("授權: GPL v3 + Commercial")
        license_label.setStyleSheet(f"font-size: 10px; color: {'#8E8E93' if not is_dark else '#98989D'};")
        license_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Copyright
        copyright_label = QLabel("© 2026 Lucien. All rights reserved.")
        copyright_label.setStyleSheet(f"font-size: 10px; color: {'#8E8E93' if not is_dark else '#98989D'};")
        copyright_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Close button
        close_btn = QPushButton("關閉")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #007AFF;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 20px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #0051D5;
            }}
        """)
        close_btn.clicked.connect(self.accept)
        
        layout.addLayout(title_layout)
        layout.addWidget(version_label)
        layout.addWidget(desc_label)
        layout.addWidget(features_label)
        layout.addStretch()
        layout.addWidget(license_label)
        layout.addWidget(copyright_label)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        
        # Set dialog background
        bg_color = "#1C1C1E" if is_dark else "#FFFFFF"
        self.setStyleSheet(f"QDialog {{ background-color: {bg_color}; }}")

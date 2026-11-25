# -*- coding: utf-8 -*-
"""
ASMR Whisper Studio - 顶部全局导航栏与底部状态栏视图组件 (ui.views.app_header_footer)
包含:
- AppHeaderBar: 顶部品牌 Logo、Mac 装饰圆点、双工作台分段切换器、GPU 状态胶囊与释放显存按钮
- AppFooterBar: 底部硬件加速引擎与状态指示栏
"""

import os
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton

_app_root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class AppHeaderBar(QFrame):
    """主窗口顶部品牌导航栏与分段工作台切换器"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("app_header_bar")
        self.setFixedHeight(54)
        header_layout = QHBoxLayout(self)
        header_layout.setContentsMargins(18, 0, 18, 0)
        header_layout.setSpacing(14)

        brand_layout = QHBoxLayout()
        brand_layout.setSpacing(8)
        mac_dots = QHBoxLayout()
        mac_dots.setSpacing(6)
        for c_fill, c_border in [("#FF5F56", "#E0443E"), ("#FFBD2E", "#DEA123"), ("#27C93F", "#1AAB29")]:
            dot = QLabel(self)
            dot.setFixedSize(11, 11)
            dot.setStyleSheet(f"background-color: {c_fill}; border: 1px solid {c_border}; border-radius: 5px;")
            mac_dots.addWidget(dot)
        brand_layout.addLayout(mac_dots)

        lbl_logo = QLabel(self)
        lbl_logo.setFixedSize(28, 28)
        lbl_logo.setAlignment(Qt.AlignCenter)
        logo_path = os.path.join(_app_root_dir, "assets", "app.png")
        if os.path.exists(logo_path):
            lbl_logo.setPixmap(QPixmap(logo_path).scaled(28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            lbl_logo.setText("🎙️")

        self.lbl_app_title = QLabel("ASMR Whisper v3.3", self)
        self.lbl_app_title.setStyleSheet("font-size: 14px; font-weight: 800; color: #18181B; letter-spacing: -0.2px;")
        brand_layout.addWidget(lbl_logo, alignment=Qt.AlignVCenter)
        brand_layout.addWidget(self.lbl_app_title, alignment=Qt.AlignVCenter)
        header_layout.addLayout(brand_layout)
        header_layout.addStretch(1)

        seg_container = QFrame(self)
        seg_container.setFixedHeight(38)
        seg_container.setMinimumWidth(380)
        seg_container.setStyleSheet("background-color: #F4F4F5; border: 1px solid #E4E4E7; border-radius: 12px; padding: 2px;")
        seg_layout = QHBoxLayout(seg_container)
        seg_layout.setContentsMargins(3, 3, 3, 3)
        seg_layout.setSpacing(4)

        self.btn_seg_transcribe = QPushButton("🎙️ ASMR 语音转录", seg_container)
        self.btn_seg_transcribe.setObjectName("seg_tab_active")
        self.btn_seg_transcribe.setMinimumWidth(165)
        self.btn_seg_transcribe.setFixedHeight(30)
        self.btn_seg_transcribe.setCursor(Qt.PointingHandCursor)

        self.btn_seg_burner = QPushButton("🎬 字幕压制与声学视窗", seg_container)
        self.btn_seg_burner.setObjectName("seg_tab_inactive")
        self.btn_seg_burner.setMinimumWidth(185)
        self.btn_seg_burner.setFixedHeight(30)
        self.btn_seg_burner.setCursor(Qt.PointingHandCursor)

        seg_layout.addWidget(self.btn_seg_transcribe)
        seg_layout.addWidget(self.btn_seg_burner)
        header_layout.addWidget(seg_container)
        header_layout.addStretch(1)

        right_header_layout = QHBoxLayout()
        right_header_layout.setSpacing(8)

        self.lbl_gpu_status = QLabel("正在检测设备...", self)
        self.btn_unload_model = QPushButton("🧹 释放显存", self)
        self.btn_unload_model.setToolTip("将已载入显存的 Whisper 模型从 GPU 中卸载，释放显存")
        self.btn_unload_model.setCursor(Qt.PointingHandCursor)
        self.btn_unload_model.setStyleSheet("""
            QPushButton { background-color: #FFFFFF; border: 1px solid #E4E4E7; border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: 600; color: #3F3F46; }
            QPushButton:hover { background-color: #F5F3FF; border-color: #DDD6FE; color: #6D28D9; }
        """)

        right_header_layout.addWidget(self.lbl_gpu_status, alignment=Qt.AlignVCenter)
        right_header_layout.addWidget(self.btn_unload_model, alignment=Qt.AlignVCenter)
        header_layout.addLayout(right_header_layout)


class AppFooterBar(QFrame):
    """主窗口底部状态与版本指示栏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("app_footer_bar")
        self.setFixedHeight(34)
        footer_layout = QHBoxLayout(self)
        footer_layout.setContentsMargins(18, 0, 18, 0)

        self.lbl_footer_left = QLabel(self)
        self.lbl_footer_left.setStyleSheet("color: #71717A; font-size: 11px;")
        self.lbl_footer_right = QLabel("ASMR Whisper Studio v3.3", self)
        self.lbl_footer_right.setStyleSheet("color: #A1A1AA; font-size: 11px;")

        footer_layout.addWidget(self.lbl_footer_left)
        footer_layout.addStretch()
        footer_layout.addWidget(self.lbl_footer_right)


__all__ = [
    "AppHeaderBar",
    "AppFooterBar",
]

# -*- coding: utf-8 -*-
"""
ASMR Whisper Studio - 压制页媒体规格参数条与对白预览横幅视图组件 (ui.views.burner_media_spec_bar)
包含:
- TimelineDialogueBanner: 时间线下方实时对白预览条与「🔄 重播此句」按钮
- MediaSpecBar: 底部 4 大区块规格参数指示条 (🎬 视频轨 / 🔊 音频轨 / ⏱️ 时长 / 💬 字幕状态)
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton


class TimelineDialogueBanner(QFrame):
    """时间线下方当前句对白预览横幅与单句重播条"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("banner_sub")
        self.setFixedHeight(34)
        self.setStyleSheet("""
            QFrame#banner_sub {
                background-color: #F8F9FB;
                border: 1px solid #E4E4E7;
                border-radius: 8px;
            }
            QFrame#banner_sub QLabel {
                border: none;
                background: transparent;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(6)

        lbl_dialogue_icon = QLabel("💬", self)
        lbl_dialogue_icon.setStyleSheet("border: none; background: transparent;")
        layout.addWidget(lbl_dialogue_icon)

        self.lbl_sub_text_preview = QLabel("未载入字幕文件（可点击右侧「浏览」或直接拖拽音视频与字幕）", self)
        self.lbl_sub_text_preview.setStyleSheet("color: #A1A1AA; font-size: 11.5px; border: none; background: transparent;")
        layout.addWidget(self.lbl_sub_text_preview, 1)

        self.btn_replay_sub = QPushButton("🔄 重播此句", self)
        self.btn_replay_sub.setStyleSheet("padding: 2px 8px; font-size: 11px; border-radius: 6px; background-color: #FFFFFF; border: 1px solid #E4E4E7;")
        self.btn_replay_sub.setEnabled(False)
        layout.addWidget(self.btn_replay_sub)


class MediaSpecBar(QFrame):
    """底部 4 大信息区块音视频工程规格指示条"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("media_spec_panel")
        self.setFixedHeight(38)
        self.setStyleSheet("""
            QFrame#media_spec_panel {
                background-color: #FFFFFF;
                border: 1px solid #E4E4E7;
                border-radius: 10px;
            }
            QFrame#media_spec_panel QLabel {
                border: none;
                background: transparent;
            }
        """)
        spec_hbox = QHBoxLayout(self)
        spec_hbox.setContentsMargins(14, 0, 14, 0)
        spec_hbox.setSpacing(10)

        def make_v_divider():
            div = QFrame(self)
            div.setFixedWidth(1)
            div.setFixedHeight(14)
            div.setStyleSheet("background-color: #E4E4E7; border: none;")
            return div

        # 区块 1: 视频轨信息
        lbl_v_icon_title = QLabel("🎬 视频", self)
        lbl_v_icon_title.setStyleSheet("color: #71717A; font-size: 11px; font-weight: 600;")
        spec_hbox.addWidget(lbl_v_icon_title)

        self.lbl_v_codec = QLabel("未载入", self)
        self.lbl_v_codec.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 600; background-color: #F4F4F5; border-radius: 4px; padding: 2px 6px;")
        spec_hbox.addWidget(self.lbl_v_codec)

        self.lbl_v_res_fps = QLabel("-- × -- | -- FPS", self)
        self.lbl_v_res_fps.setStyleSheet("color: #52525B; font-size: 11px; font-weight: 500;")
        spec_hbox.addWidget(self.lbl_v_res_fps)

        spec_hbox.addWidget(make_v_divider())

        # 区块 2: 音频轨信息
        lbl_a_icon_title = QLabel("🔊 音频", self)
        lbl_a_icon_title.setStyleSheet("color: #71717A; font-size: 11px; font-weight: 600;")
        spec_hbox.addWidget(lbl_a_icon_title)

        self.lbl_a_codec = QLabel("未载入", self)
        self.lbl_a_codec.setStyleSheet("color: #18181B; font-size: 11px; font-weight: 600; background-color: #F4F4F5; border-radius: 4px; padding: 2px 6px;")
        spec_hbox.addWidget(self.lbl_a_codec)

        self.lbl_a_rate_ch = QLabel("--", self)
        self.lbl_a_rate_ch.setStyleSheet("color: #52525B; font-size: 11px; font-weight: 500;")
        spec_hbox.addWidget(self.lbl_a_rate_ch)

        spec_hbox.addWidget(make_v_divider())

        # 区块 3: 媒体时长
        lbl_dur_icon_title = QLabel("⏱️ 时长", self)
        lbl_dur_icon_title.setStyleSheet("color: #71717A; font-size: 11px; font-weight: 600;")
        spec_hbox.addWidget(lbl_dur_icon_title)

        self.lbl_total_dur = QLabel("--:--", self)
        self.lbl_total_dur.setStyleSheet("color: #18181B; font-size: 11.5px; font-weight: 600; font-family: monospace;")
        spec_hbox.addWidget(self.lbl_total_dur)

        spec_hbox.addWidget(make_v_divider())

        # 区块 4: 字幕状态
        lbl_sub_icon_title = QLabel("💬 字幕", self)
        lbl_sub_icon_title.setStyleSheet("color: #71717A; font-size: 11px; font-weight: 600;")
        spec_hbox.addWidget(lbl_sub_icon_title)

        self.lbl_sub_status = QLabel("未载入", self)
        self.lbl_sub_status.setStyleSheet("color: #A1A1AA; font-size: 11px; font-weight: 500;")
        spec_hbox.addWidget(self.lbl_sub_status)

        spec_hbox.addStretch()


__all__ = [
    "TimelineDialogueBanner",
    "MediaSpecBar",
]

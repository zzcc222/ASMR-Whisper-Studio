# -*- coding: utf-8 -*-
"""
ASMR Whisper Studio - 实时字幕预览面板组件 (ui.components.concurrent_subtitle_view)
- 保持宽敞通透的单一大窗口 (txt_subtitles) 呈现字幕卡片流
- 顶部配备专属工具条（与「运行详细日志」页视觉对齐）：
  1. 任务选择下拉栏 (combo_preview_task)：实时识别并展示各任务名称、状态 (⏳等待 / ⚡转录中 / ✅已完成) 与已生成句数，支持 6 行定高丝滑滚动
  2. 当前任务句数统计标签 (lbl_seg_count)
  3. 自动切换开关按钮 (btn_auto_follow)：支持「🔄 自动切换」与「📌 已固定当前」一键切换；用户手动选定任务后自动锁定不乱跳
"""

from typing import Dict, List
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTextEdit, QListView, QAbstractItemView
)


class ConcurrentSubtitleView(QWidget):
    """单大窗 + 顶部任务选择栏 + 自动切换开关的实时字幕预览容器"""

    sig_user_selected_task = Signal(int)      # 用户手动在下拉栏选择了某个任务 (file_idx)
    sig_auto_follow_toggled = Signal(bool)    # 用户手动点击切换了「自动切换 / 已固定当前」按钮

    def __init__(self, parent=None):
        super().__init__(parent)
        self._task_row_map: Dict[int, int] = {}  # file_idx -> combo row index
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(6)

        # 1. 顶部字幕预览工具栏 (与隔壁日志页 log_bar_layout 高度和边距完全一致)
        bar_layout = QHBoxLayout()
        bar_layout.setContentsMargins(2, 0, 2, 0)
        bar_layout.setSpacing(6)

        self.lbl_task_prefix = QLabel("🎯 预览任务:", self)
        self.lbl_task_prefix.setStyleSheet("color: #71717A; font-size: 11px; font-weight: 600;")
        bar_layout.addWidget(self.lbl_task_prefix)

        # 任务选择下拉框 (带 6 行定高丝滑滚动样式)
        self.combo_preview_task = QComboBox(self)
        self.combo_preview_task.setMinimumWidth(260)
        task_view = QListView(self.combo_preview_task)
        task_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        task_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        task_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.combo_preview_task.setView(task_view)
        self.combo_preview_task.setMaxVisibleItems(6)
        self.combo_preview_task.setStyleSheet("""
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #E4E4E7;
                border-radius: 6px;
                padding: 2px 10px;
                font-size: 11.5px;
                font-weight: 600;
                color: #18181B;
                min-height: 20px;
                combobox-popup: 0;
            }
            QComboBox:hover {
                border-color: #C4B5FD;
                background-color: #FAFAFF;
            }
            QComboBox:disabled {
                background-color: #F4F4F5;
                color: #A1A1AA;
                border-color: #E4E4E7;
            }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #E4E4E7;
                border-radius: 8px;
                padding: 4px;
                outline: none;
                selection-background-color: #F5F3FF;
                selection-color: #6D28D9;
            }
            QComboBox QAbstractItemView::item {
                min-height: 26px;
                padding: 2px 8px;
                border-radius: 5px;
                color: #18181B;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: #F5F3FF;
                color: #6D28D9;
            }
            QComboBox QAbstractItemView::item:selected {
                background-color: #EDE9FE;
                color: #6D28D9;
                font-weight: 700;
            }
            QComboBox QAbstractItemView QScrollBar:vertical {
                background: #FAFAFA;
                width: 7px;
                margin: 2px 1px 2px 1px;
                border-radius: 3px;
            }
            QComboBox QAbstractItemView QScrollBar::handle:vertical {
                background: #D4D4D8;
                min-height: 26px;
                border-radius: 3px;
            }
            QComboBox QAbstractItemView QScrollBar::handle:vertical:hover {
                background: #8B5CF6;
            }
            QComboBox QAbstractItemView QScrollBar::add-line:vertical,
            QComboBox QAbstractItemView QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        self.combo_preview_task.addItem("⚪ 等待转录任务启动...", -1)
        self.combo_preview_task.setEnabled(False)
        # activated 信号仅在用户手动点选下拉项时触发，程序调用 setCurrentIndex 不会触发
        self.combo_preview_task.activated.connect(self._on_combo_activated)
        bar_layout.addWidget(self.combo_preview_task, 1)

        bar_layout.addStretch()

        # 当前预览任务句数统计
        self.lbl_seg_count = QLabel("💬 0 句", self)
        self.lbl_seg_count.setStyleSheet(
            "color: #6D28D9; background-color: #F5F3FF; border: 1px solid #DDD6FE; "
            "border-radius: 6px; padding: 2px 8px; font-size: 11px; font-weight: 600;"
        )
        bar_layout.addWidget(self.lbl_seg_count)

        # 自动切换 / 锁定当前任务 按钮
        self.btn_auto_follow = QPushButton("🔄 自动切换", self)
        self.btn_auto_follow.setCheckable(True)
        self.btn_auto_follow.setChecked(True)
        self.btn_auto_follow.setCursor(Qt.PointingHandCursor)
        self.btn_auto_follow.toggled.connect(self._on_auto_follow_toggled)
        self._update_auto_follow_btn_style(True)
        bar_layout.addWidget(self.btn_auto_follow)

        layout.addLayout(bar_layout)

        # 2. 下方单一大窗口实时字幕文本框 (100% 独占展示空间)
        self.txt_subtitles = QTextEdit(self)
        self.txt_subtitles.setReadOnly(True)
        self.txt_subtitles.document().setMaximumBlockCount(3000)
        self.txt_subtitles.setPlaceholderText("转录开始后，实时生成的句子与时间戳将在此处优雅滚动展示……")
        layout.addWidget(self.txt_subtitles, 1)

    def _update_auto_follow_btn_style(self, checked: bool):
        if checked:
            self.btn_auto_follow.setText("🔄 自动切换")
            self.btn_auto_follow.setToolTip(
                "已开启自动切换：当前观看的任务完成后，将自动切换到下一个正在转录的任务\n"
                "（手动在下拉框选择任务或点击此按钮可固定当前任务）"
            )
            self.btn_auto_follow.setStyleSheet("""
                QPushButton {
                    background-color: #F5F3FF;
                    color: #7C3AED;
                    border: 1px solid #DDD6FE;
                    border-radius: 6px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #EDE9FE;
                    border-color: #C4B5FD;
                }
            """)
        else:
            self.btn_auto_follow.setText("📌 已固定当前")
            self.btn_auto_follow.setToolTip(
                "已固定当前观看的任务：即使后台开启新任务或当前任务完成，画面也不会自动跳转\n"
                "（点击此按钮可重新开启自动切换跟随）"
            )
            self.btn_auto_follow.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    color: #52525B;
                    border: 1px solid #E4E4E7;
                    border-radius: 6px;
                    padding: 3px 10px;
                    font-size: 11px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #F4F4F5;
                    border-color: #D4D4D8;
                    color: #18181B;
                }
            """)

    def _on_combo_activated(self, combo_idx: int):
        if combo_idx < 0 or combo_idx >= self.combo_preview_task.count():
            return
        file_idx = self.combo_preview_task.itemData(combo_idx)
        if file_idx is not None and int(file_idx) >= 0:
            self.sig_user_selected_task.emit(int(file_idx))

    def _on_auto_follow_toggled(self, checked: bool):
        self._update_auto_follow_btn_style(checked)
        self.sig_auto_follow_toggled.emit(checked)

    def set_auto_follow_state(self, enabled: bool):
        """由控制器编程式同步自动切换按钮状态，不触发递归信号"""
        self.btn_auto_follow.blockSignals(True)
        self.btn_auto_follow.setChecked(enabled)
        self._update_auto_follow_btn_style(enabled)
        self.btn_auto_follow.blockSignals(False)

    @staticmethod
    def format_task_label(file_idx: int, total_files: int, fname: str, status: str, seg_count: int) -> str:
        """格式化下拉选项中的任务状态与名称"""
        ratio = f"#{file_idx + 1}/{total_files}" if total_files > 1 else f"#{file_idx + 1}"
        if status == "running":
            return f"⚡ [{ratio} 正在转录 · {seg_count}句] {fname}"
        elif status == "done":
            return f"✅ [{ratio} 已完成 · {seg_count}句] {fname}"
        elif status == "error":
            return f"⚠️ [{ratio} 已结束 · {seg_count}句] {fname}"
        else:
            return f"⏳ [{ratio} 排队等待] {fname}"

    def init_task_list(self, file_names: List[str]):
        """在批量任务启动时初始化下拉选择栏中的所有任务项"""
        self.combo_preview_task.blockSignals(True)
        self.combo_preview_task.clear()
        self._task_row_map.clear()
        total = len(file_names)
        if total == 0:
            self.combo_preview_task.addItem("⚪ 等待转录任务启动...", -1)
            self.combo_preview_task.setEnabled(False)
        else:
            for idx, fname in enumerate(file_names):
                label = self.format_task_label(idx, total, fname, "waiting", 0)
                self.combo_preview_task.addItem(label, idx)
                self._task_row_map[idx] = idx
            self.combo_preview_task.setEnabled(True)
        self.combo_preview_task.blockSignals(False)

    def upsert_task_item(self, file_idx: int, total_files: int, fname: str, status: str, seg_count: int):
        """实时更新下拉栏中某个任务的状态描述与句数（静默更新，不打断用户当前选中项）"""
        label = self.format_task_label(file_idx, total_files, fname, status, seg_count)
        self.combo_preview_task.blockSignals(True)
        try:
            # 若此前仅有默认占位项，先清空占位项
            if self.combo_preview_task.count() == 1 and self.combo_preview_task.itemData(0) == -1:
                self.combo_preview_task.clear()
                self._task_row_map.clear()

            if file_idx in self._task_row_map:
                row = self._task_row_map[file_idx]
                if 0 <= row < self.combo_preview_task.count():
                    self.combo_preview_task.setItemText(row, label)
            else:
                row = self.combo_preview_task.count()
                self.combo_preview_task.addItem(label, file_idx)
                self._task_row_map[file_idx] = row
            self.combo_preview_task.setEnabled(True)
        finally:
            self.combo_preview_task.blockSignals(False)

    def set_selected_task(self, file_idx: int, seg_count: int = 0):
        """编程式将下拉框选中项同步至 file_idx"""
        self.lbl_seg_count.setText(f"💬 {seg_count} 句")
        if file_idx not in self._task_row_map:
            return
        row = self._task_row_map[file_idx]
        if 0 <= row < self.combo_preview_task.count() and self.combo_preview_task.currentIndex() != row:
            self.combo_preview_task.blockSignals(True)
            self.combo_preview_task.setCurrentIndex(row)
            self.combo_preview_task.blockSignals(False)

    def update_current_seg_count(self, seg_count: int):
        self.lbl_seg_count.setText(f"💬 {seg_count} 句")

    def reset_all(self):
        """重置预览大窗口与顶部选项栏"""
        self.txt_subtitles.clear()
        self.combo_preview_task.blockSignals(True)
        self.combo_preview_task.clear()
        self._task_row_map.clear()
        self.combo_preview_task.addItem("⚪ 等待转录任务启动...", -1)
        self.combo_preview_task.setEnabled(False)
        self.combo_preview_task.blockSignals(False)
        self.lbl_seg_count.setText("💬 0 句")
        self.set_auto_follow_state(True)


__all__ = [
    "ConcurrentSubtitleView",
]

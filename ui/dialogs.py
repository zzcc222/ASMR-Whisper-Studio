# -*- coding: utf-8 -*-
"""
ASMR Whisper Studio - 弹窗组件集合 (PromptRecognizerDialog & SubtitleEditDialog)
"""

import os
import sys
from typing import List, Dict, Any
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QListWidget, QListWidgetItem, QMessageBox,
    QLineEdit, QWidget
)

from core.subtitle.subtitle_parser import parse_time_to_ms
from core.subtitle.subtitle_exporter import format_timestamp
from ui.styles import setup_dwm_light_titlebar


class PromptRecognizerDialog(QDialog):
    """
    智能提示词文档解析与识别确认弹窗
    """
    def __init__(self, templates: List[dict], parent=None, file_path=""):
        super().__init__(parent)
        self.setWindowTitle("📄 提示词文档解析与识别")
        self.resize(760, 520)
        self.selected_prompt = ""
        self.selected_title = ""
        self.templates = [dict(t) for t in templates] if templates else []
        self._current_row = -1
        self.file_path = file_path
        self._init_ui()

    def showEvent(self, event):
        super().showEvent(event)
        try:
            setup_dwm_light_titlebar(int(self.winId()))
        except Exception:
            pass

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        fname = os.path.basename(self.file_path) if self.file_path else "文档"
        top_lbl = QLabel(f"📂 已解析文档: <b>{fname}</b> | 共识别出 <b>{len(self.templates)}</b> 个提示词选项")
        top_lbl.setStyleSheet("color: #7C3AED; font-size: 13px; font-weight: bold;")
        layout.addWidget(top_lbl)

        content_layout = QHBoxLayout()

        # 左侧列表
        left_box = QVBoxLayout()
        left_box.addWidget(QLabel("选择识别到的模板/段落:"))
        self.list_templates = QListWidget()
        self.list_templates.setStyleSheet("""
            QListWidget {
                background-color: #FFFFFF;
                border: 1px solid #E4E4E7;
                border-radius: 8px;
                color: #18181B;
                outline: none;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-bottom: 1px solid #F4F4F5;
            }
            QListWidget::item:selected {
                background-color: #F5F3FF;
                color: #6D28D9;
                font-weight: bold;
            }
        """)
        for idx, item in enumerate(self.templates, 1):
            title = item.get("title", f"模板 {idx}")
            self.list_templates.addItem(QListWidgetItem(f"📌 {title}"))

        self.list_templates.currentRowChanged.connect(self._on_template_selected)
        left_box.addWidget(self.list_templates)
        content_layout.addLayout(left_box, 2)

        # 右侧预览与微调
        right_box = QVBoxLayout()
        self.lbl_item_title = QLabel("提示词正文预览与微调:")
        self.lbl_item_title.setStyleSheet("color: #18181B; font-weight: bold;")
        right_box.addWidget(self.lbl_item_title)

        self.txt_preview = QTextEdit()
        self.txt_preview.setStyleSheet("""
            QTextEdit {
                background-color: #FAFAFA;
                border: 1px solid #E4E4E7;
                border-radius: 8px;
                color: #18181B;
                font-size: 13px;
                padding: 8px;
            }
            QTextEdit:focus {
                border: 1px solid #8B5CF6;
                background-color: #FFFFFF;
            }
        """)
        self.txt_preview.textChanged.connect(self._on_preview_text_changed)
        right_box.addWidget(self.txt_preview)

        # 长度与截取条
        status_row = QHBoxLayout()
        self.lbl_stats = QLabel("字数: 0 | 状态: 就绪")
        self.lbl_stats.setStyleSheet("color: #71717A; font-size: 11px;")
        self.btn_truncate = QPushButton("✂️ 智能截取前 180 字 (Whisper 最佳推荐)")
        self.btn_truncate.setStyleSheet("font-size: 11px; padding: 4px 10px; background-color: #F5F3FF; color: #6D28D9; border: 1px solid #DDD6FE; border-radius: 6px;")
        self.btn_truncate.clicked.connect(self._truncate_text)
        self.btn_truncate.setVisible(False)

        status_row.addWidget(self.lbl_stats)
        status_row.addStretch()
        status_row.addWidget(self.btn_truncate)
        right_box.addLayout(status_row)

        content_layout.addLayout(right_box, 3)
        layout.addLayout(content_layout)

        # 底部操作栏
        btn_box = QHBoxLayout()
        tip_lbl = QLabel("💡 提示：Whisper 提示词建议控制在 100~180 字以内，模型可精准理解语境并杜绝幻听。")
        tip_lbl.setStyleSheet("color: #71717A; font-size: 11px;")
        btn_box.addWidget(tip_lbl)
        btn_box.addStretch()

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_apply = QPushButton("✅ 应用此提示词")
        self.btn_apply.setObjectName("btn_primary")
        self.btn_apply.clicked.connect(self._on_apply)

        btn_box.addWidget(self.btn_cancel)
        btn_box.addWidget(self.btn_apply)
        layout.addLayout(btn_box)

        if self.templates:
            self.list_templates.setCurrentRow(0)

    def _on_template_selected(self, row: int):
        if 0 <= self._current_row < len(self.templates):
            self.templates[self._current_row]["text"] = self.txt_preview.toPlainText()
        self._current_row = row
        if 0 <= row < len(self.templates):
            item = self.templates[row]
            self.lbl_item_title.setText(f"📌 {item.get('title', '提示词正文')}:")
            self.txt_preview.setPlainText(item.get("text", ""))

    def _on_preview_text_changed(self):
        text = self.txt_preview.toPlainText().strip()
        length = len(text)
        if length == 0:
            self.lbl_stats.setText("字数: 0 | ⚠️ 内容为空")
            self.lbl_stats.setStyleSheet("color: #EF4444; font-size: 11px;")
            self.btn_truncate.setVisible(False)
            self.btn_apply.setEnabled(False)
        elif length <= 180:
            self.lbl_stats.setText(f"字数: {length} 字符 | 状态: 🟢 极佳 (在 Whisper 推荐范围 ≤ 180 字符)")
            self.lbl_stats.setStyleSheet("color: #10B981; font-size: 11px; font-weight: 600;")
            self.btn_truncate.setVisible(False)
            self.btn_apply.setEnabled(True)
        elif length <= 250:
            self.lbl_stats.setText(f"字数: {length} 字符 | 状态: 🟡 接近上限 (Whisper 最多接收约 224 tokens)")
            self.lbl_stats.setStyleSheet("color: #F59E0B; font-size: 11px; font-weight: 600;")
            self.btn_truncate.setVisible(True)
            self.btn_apply.setEnabled(True)
        else:
            self.lbl_stats.setText(f"字数: {length} 字符 | 状态: 🟠 超出上限 (超出部分将被底层截断)")
            self.lbl_stats.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 600;")
            self.btn_truncate.setVisible(True)
            self.btn_apply.setEnabled(True)

    def _truncate_text(self):
        text = self.txt_preview.toPlainText().strip()
        if len(text) > 180:
            sub = text[:180]
            puncts = ["。", "！", "？", "…", "、", "!", "?"]
            best_cut = -1
            for p in puncts:
                idx = sub.rfind(p)
                if idx > 120 and idx > best_cut:
                    best_cut = idx + 1
            if best_cut > 0:
                truncated = sub[:best_cut]
            else:
                truncated = sub + "……"
            self.txt_preview.setPlainText(truncated)

    def _on_apply(self):
        text = self.txt_preview.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "提示词内容不能为空！")
            return
        if 0 <= self._current_row < len(self.templates):
            self.templates[self._current_row]["text"] = self.txt_preview.toPlainText()
        self.selected_prompt = text
        row = self.list_templates.currentRow()
        if 0 <= row < len(self.templates):
            self.selected_title = self.templates[row].get("title", f"模板 {row+1}")
        else:
            self.selected_title = "导入提示词"
        self.accept()


class SubtitleEditDialog(QDialog):
    """极简高颜值字幕单句微调弹窗 (支持起止时间轴毫秒微调与台词文本修正)"""

    def __init__(self, sub_data: Dict[str, Any], index: int = 0, parent: QWidget = None):
        super().__init__(parent)
        self.setWindowTitle(f"✏️ 微调第 #{index + 1} 句字幕")
        self.setMinimumWidth(460)
        self.sub_data = dict(sub_data)
        self._init_ui(index)

    def _init_ui(self, index: int):
        self.setStyleSheet("""
            QDialog {
                background-color: #FFFFFF;
                font-family: "Microsoft YaHei UI", "Segoe UI", sans-serif;
            }
            QLabel {
                color: #18181B;
                font-size: 12px;
                background: transparent;
            }
            QLineEdit {
                background-color: #F8FAFC;
                border: 1px solid #E4E4E7;
                border-radius: 8px;
                padding: 7px 10px;
                color: #18181B;
                font-size: 12.5px;
            }
            QLineEdit:focus {
                border: 1.5px solid #8B5CF6;
                background-color: #FFFFFF;
            }
            QPushButton {
                background-color: #F4F4F5;
                border: 1px solid #E4E4E7;
                border-radius: 7px;
                padding: 5px 10px;
                color: #18181B;
                font-size: 11.5px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #F5F3FF;
                border-color: #C4B5FD;
                color: #6D28D9;
            }
            QPushButton#BtnSaveDialog {
                background-color: #8B5CF6;
                border: none;
                color: #FFFFFF;
                padding: 7px 18px;
                font-weight: 700;
            }
            QPushButton#BtnSaveDialog:hover {
                background-color: #7C3AED;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        lbl_head = QLabel(f"正在编辑第 #{index + 1} 句台词与时间轴")
        lbl_head.setStyleSheet("font-size: 13.5px; font-weight: 700; color: #18181B;")
        layout.addWidget(lbl_head)

        # 起始时间行
        row_start = QHBoxLayout()
        lbl_s = QLabel("起始时间:")
        lbl_s.setFixedWidth(64)
        self.edit_start = QLineEdit(str(self.sub_data.get("start_str", "0:00:00.00")))
        btn_s_minus = QPushButton("-0.1s")
        btn_s_plus = QPushButton("+0.1s")
        btn_s_minus.clicked.connect(lambda: self._shift_time(self.edit_start, -100))
        btn_s_plus.clicked.connect(lambda: self._shift_time(self.edit_start, 100))
        row_start.addWidget(lbl_s)
        row_start.addWidget(self.edit_start, 1)
        row_start.addWidget(btn_s_minus)
        row_start.addWidget(btn_s_plus)
        layout.addLayout(row_start)

        # 结束时间行
        row_end = QHBoxLayout()
        lbl_e = QLabel("结束时间:")
        lbl_e.setFixedWidth(64)
        self.edit_end = QLineEdit(str(self.sub_data.get("end_str", "0:00:02.00")))
        btn_e_minus = QPushButton("-0.1s")
        btn_e_plus = QPushButton("+0.1s")
        btn_e_minus.clicked.connect(lambda: self._shift_time(self.edit_end, -100))
        btn_e_plus.clicked.connect(lambda: self._shift_time(self.edit_end, 100))
        row_end.addWidget(lbl_e)
        row_end.addWidget(self.edit_end, 1)
        row_end.addWidget(btn_e_minus)
        row_end.addWidget(btn_e_plus)
        layout.addLayout(row_end)

        # 台词文本行
        lbl_t = QLabel("台词文本:")
        layout.addWidget(lbl_t)
        self.edit_text = QLineEdit(str(self.sub_data.get("text", "")))
        self.edit_text.setPlaceholderText("请输入字幕台词内容...")
        layout.addWidget(self.edit_text)

        self.lbl_err = QLabel("")
        self.lbl_err.setStyleSheet("color: #EF4444; font-size: 11px;")
        self.lbl_err.hide()
        layout.addWidget(self.lbl_err)

        # 底部按钮
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_ok = QPushButton("确定修改")
        btn_ok.setObjectName("BtnSaveDialog")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self._on_accept)
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)

        self.edit_text.setFocus()
        self.edit_text.selectAll()

    def _shift_time(self, line_edit: QLineEdit, delta_ms: int):
        ms = parse_time_to_ms(line_edit.text())
        if ms is None:
            ms = 0
        new_ms = max(0, ms + delta_ms)
        fmt = "srt" if "," in line_edit.text() else "ass"
        line_edit.setText(format_timestamp(new_ms / 1000.0, fmt))

    def _on_accept(self):
        s_ms = parse_time_to_ms(self.edit_start.text())
        e_ms = parse_time_to_ms(self.edit_end.text())
        txt = self.edit_text.text().strip()
        if s_ms is None or e_ms is None:
            self.lbl_err.setText("⚠️ 时间格式无效，请使用 H:MM:SS.cc 或 HH:MM:SS,mmm 格式")
            self.lbl_err.show()
            return
        if e_ms <= s_ms:
            self.lbl_err.setText("⚠️ 结束时间必须大于起始时间")
            self.lbl_err.show()
            return
        if not txt:
            self.lbl_err.setText("⚠️ 台词内容不能为空")
            self.lbl_err.show()
            return
        fmt = "srt" if "," in self.edit_start.text() else "ass"
        self.sub_data["start_ms"] = s_ms
        self.sub_data["end_ms"] = e_ms
        self.sub_data["start_str"] = format_timestamp(s_ms / 1000.0, fmt)
        self.sub_data["end_str"] = format_timestamp(e_ms / 1000.0, fmt)
        self.sub_data["text"] = txt
        self.accept()


__all__ = [
    "PromptRecognizerDialog",
    "SubtitleEditDialog",
]

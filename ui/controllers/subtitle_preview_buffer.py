# -*- coding: utf-8 -*-
"""
ASMR Whisper Studio - 多任务并发实时字幕预览缓存与视图切换器 (ui.controllers.subtitle_preview_buffer)
- 为每个文件 (file_idx) 维护独立的字幕 HTML 卡片流缓存，杜绝多任务并发时不同文件的台词交叉混排
- 保持单一大窗口 (txt_subtitles) 宽敞展示，并驱动顶部任务选择栏 (combo_preview_task) 实时刷新各任务状态与句数
- 严谨实现「🔄 自动切换」与「📌 已固定当前」逻辑：
  * 开启自动切换时：当前观看任务未结束前绝不乱跳；当前观看任务完成后自动切换到下一个正在转录的任务
  * 手动选择观看某任务后：自动切换为「📌 已固定当前」，新任务启动或当前任务结束时均绝不自动跳转
"""

import os
import html
from typing import Any, Dict, List, Optional, Set
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import QTextEdit

from core.subtitle.subtitle_exporter import format_timestamp


def format_segment_card_html(start: float, end: float, text: str) -> str:
    """构建统一的字幕预览行 HTML 卡片"""
    time_tag = f"{format_timestamp(start, 'srt')} → {format_timestamp(end, 'srt')}"
    escaped_text = html.escape(text)
    return (
        f'<div style="background-color:#FFFFFF; border:1px solid #E4E4E7; border-radius:8px; padding:5px 10px; margin:4px 0;">'
        f'<span style="background-color:#F5F3FF; color:#6D28D9; border:1px solid #DDD6FE; border-radius:4px; padding:1px 6px; font-size:11px; font-weight:700; font-family:monospace;">{time_tag}</span> '
        f'<span style="color:#18181B; font-size:12px; font-weight:500; margin-left:6px;">{escaped_text}</span>'
        f"</div>"
    )


def format_file_header_html(idx: int, total_files: int, fname: str) -> str:
    """构建文件起始标题头 HTML"""
    escaped_fname = html.escape(fname)
    return (
        f'<div style="background-color:#F4F4F5; border-left:3px solid #8B5CF6; padding:5px 10px; margin-top:8px; margin-bottom:6px; border-radius:4px;">'
        f'<b style="color:#18181B; font-size:12px;">▶ [{idx + 1}/{total_files}] {escaped_fname}</b>'
        f"</div>"
    )


class SubtitlePreviewBuffer:
    """多任务并发字幕预览隔离缓存与单大窗选择器联动控制器"""

    def __init__(self, text_edit: QTextEdit, multi_view: Optional[Any] = None):
        self.text_edit = text_edit
        self.multi_view = None
        self.headers: Dict[int, str] = {}
        self.file_names: Dict[int, str] = {}
        self.file_status: Dict[int, str] = {}
        self.segments_html: Dict[int, List[str]] = {}
        self.footers: Dict[int, str] = {}
        self.active_indices: Set[int] = set()
        self.total_files: int = 1
        self.focused_idx: int = -1
        self.auto_follow: bool = True  # True: 🔄 自动切换; False: 📌 已固定当前 (手动选择后不跳转)

        if multi_view is not None:
            self.attach_multi_view(multi_view)

    @property
    def user_pinned(self) -> bool:
        return not self.auto_follow

    @user_pinned.setter
    def user_pinned(self, val: bool):
        self.set_auto_follow(not bool(val))

    def attach_multi_view(self, multi_view: Any):
        if self.multi_view is multi_view or multi_view is None:
            return
        self.multi_view = multi_view
        self.multi_view.sig_user_selected_task.connect(
            lambda idx: self.switch_focus(idx, pinned_by_user=True)
        )
        self.multi_view.sig_auto_follow_toggled.connect(self.set_auto_follow)

    def clear(self):
        self.headers.clear()
        self.file_names.clear()
        self.file_status.clear()
        self.segments_html.clear()
        self.footers.clear()
        self.active_indices.clear()
        self.total_files = 1
        self.focused_idx = -1
        self.auto_follow = True
        if self.multi_view is not None:
            self.multi_view.reset_all()
        elif self.text_edit is not None:
            self.text_edit.clear()

    def prepare_batch(self, file_paths: List[str]):
        """在批量任务启动瞬间预填充所有待处理文件名至顶部下拉选择栏"""
        self.clear()
        names = [os.path.basename(p) for p in (file_paths or [])]
        self.total_files = max(1, len(names))
        for idx, name in enumerate(names):
            self.file_names[idx] = name
            self.file_status[idx] = "waiting"
            self.headers[idx] = format_file_header_html(idx, self.total_files, name)
            self.segments_html[idx] = []
        if self.multi_view is not None:
            self.multi_view.init_task_list(names)

    def _sync_combo_item(self, idx: int):
        if self.multi_view is None:
            return
        fname = self.file_names.get(idx, f"任务 #{idx + 1}")
        st = self.file_status.get(idx, "waiting")
        seg_cnt = len(self.segments_html.get(idx, []))
        self.multi_view.upsert_task_item(idx, self.total_files, fname, st, seg_cnt)
        if idx == self.focused_idx:
            self.multi_view.update_current_seg_count(seg_cnt)

    def _set_focus_internal(self, idx: int):
        """内部切换当前大窗口展示的目标任务 (不改变 auto_follow 锁定状态)"""
        self.focused_idx = idx
        self._render_focused_file()
        if self.multi_view is not None:
            seg_cnt = len(self.segments_html.get(idx, []))
            self.multi_view.set_selected_task(idx, seg_count=seg_cnt)

    def on_file_started(self, idx: int, total_files: int, fname: str):
        self.total_files = max(1, total_files)
        self.file_names[idx] = fname
        self.file_status[idx] = "running"
        self.headers[idx] = format_file_header_html(idx, self.total_files, fname)
        self.segments_html[idx] = []
        self.footers.pop(idx, None)
        self.active_indices.add(idx)

        self._sync_combo_item(idx)

        # 仅在初始尚无聚焦任务，或开启了「🔄 自动切换」且当前所看任务已经结束时，才切换到新启动的任务
        if self.focused_idx == -1:
            self._set_focus_internal(idx)
        elif self.auto_follow and self.focused_idx not in self.active_indices:
            self._set_focus_internal(idx)

    def on_segment(self, idx: int, start: float, end: float, text: str):
        card_html = format_segment_card_html(start, end, text)
        if idx not in self.segments_html:
            self.segments_html[idx] = []
        self.segments_html[idx].append(card_html)

        self._sync_combo_item(idx)

        if idx == self.focused_idx and self.text_edit is not None:
            self.text_edit.append(card_html)
            self.text_edit.moveCursor(QTextCursor.End)
            self.text_edit.ensureCursorVisible()

    def on_segments_refined(self, idx: int, segments: list):
        refined_cards: List[str] = []
        for seg in segments or []:
            s_start = float(seg.get("start", 0.0))
            s_end = float(seg.get("end", 0.0))
            s_text = str(seg.get("text", "")).strip()
            if s_text:
                refined_cards.append(format_segment_card_html(s_start, s_end, s_text))
        self.segments_html[idx] = refined_cards
        self._sync_combo_item(idx)

        if idx == self.focused_idx:
            self._render_focused_file()

    def on_file_finished(self, idx: int, finish_html: str):
        self.footers[idx] = finish_html
        self.file_status[idx] = "done"
        self.active_indices.discard(idx)
        self._sync_combo_item(idx)

        if idx == self.focused_idx and self.text_edit is not None:
            self.text_edit.append(finish_html)
            self.text_edit.moveCursor(QTextCursor.End)
            self.text_edit.ensureCursorVisible()

            # 仅当「🔄 自动切换」开启且后台仍有正在转录的其它任务时，才自动跳转到下一个活跃任务
            if self.auto_follow and self.active_indices:
                next_active = min(self.active_indices)
                self._set_focus_internal(next_active)

    def on_file_failed(self, idx: int, fail_html: str):
        self.footers[idx] = fail_html
        self.file_status[idx] = "error"
        self.active_indices.discard(idx)
        self._sync_combo_item(idx)

        if idx == self.focused_idx and self.text_edit is not None:
            self.text_edit.append(fail_html)
            self.text_edit.moveCursor(QTextCursor.End)
            self.text_edit.ensureCursorVisible()

            if self.auto_follow and self.active_indices:
                next_active = min(self.active_indices)
                self._set_focus_internal(next_active)

    def set_auto_follow(self, enabled: bool):
        """切换「🔄 自动切换」与「📌 已固定当前」模式"""
        self.auto_follow = bool(enabled)
        if self.multi_view is not None:
            self.multi_view.set_auto_follow_state(self.auto_follow)

        # 若用户重新开启了「🔄 自动切换」，且当前观看的任务已结束、后台有正在运行的任务，立即跳转跟上
        if self.auto_follow and self.focused_idx not in self.active_indices and self.active_indices:
            self._set_focus_internal(min(self.active_indices))

    def switch_focus(self, idx: int, pinned_by_user: bool = True):
        """
        切换大窗口展示的任务 idx：
        当 pinned_by_user=True (用户从顶部下拉框或左侧队列表格手动点击) 时，
        立即将自动切换关闭为「📌 已固定当前」，新任务启动或结束时绝不自动跳转！
        """
        if idx < 0:
            return
        if (
            idx not in self.file_names
            and idx not in self.headers
            and idx not in self.segments_html
            and idx not in self.footers
        ):
            return
        if pinned_by_user:
            self.auto_follow = False
            if self.multi_view is not None:
                self.multi_view.set_auto_follow_state(False)
        self._set_focus_internal(idx)

    def _render_focused_file(self):
        if self.text_edit is None or self.focused_idx < 0:
            return
        idx = self.focused_idx
        self.text_edit.setUpdatesEnabled(False)
        try:
            self.text_edit.clear()
            hdr = self.headers.get(idx)
            if hdr:
                self.text_edit.append(hdr)
            for card in self.segments_html.get(idx, []):
                self.text_edit.append(card)
            ftr = self.footers.get(idx)
            if ftr:
                self.text_edit.append(ftr)
            self.text_edit.moveCursor(QTextCursor.End)
            self.text_edit.ensureCursorVisible()
        finally:
            self.text_edit.setUpdatesEnabled(True)


__all__ = [
    "format_segment_card_html",
    "format_file_header_html",
    "SubtitlePreviewBuffer",
]

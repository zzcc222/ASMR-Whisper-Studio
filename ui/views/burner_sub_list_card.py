# -*- coding: utf-8 -*-
"""
ASMR Whisper Studio - 实时字幕对白列表与在线微调卡片组件 (BurnerSubListCard)
展示当前已载入的全部台词分句、支持关键词实时过滤搜索、点击跳转、
双击/右键在线微调台词与时间轴、增删字幕行以及一键回写保存磁盘。
"""

from typing import List, Dict, Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QAbstractItemView, QWidget, QDialog,
    QMenu
)

from core.subtitle.subtitle_exporter import format_timestamp
from ui.dialogs import SubtitleEditDialog


class BurnerSubListCard(QFrame):
    """实时字幕对白列表与在线编辑卡片组件"""

    sig_item_clicked = Signal(dict)
    sig_subtitles_modified = Signal()
    sig_save_requested = Signal()
    sig_add_requested = Signal(int)
    sig_delete_requested = Signal(int)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self.setObjectName("apple_card")
        self._items_ref: List[Dict[str, Any]] = []
        self._has_unsaved_changes: bool = False
        self._init_ui()

    def _init_ui(self):
        card_sub_layout = QVBoxLayout(self)
        card_sub_layout.setContentsMargins(20, 14, 20, 14)
        card_sub_layout.setSpacing(10)

        # 第一行：标题、计数徽章、搜索框与操作按钮
        sub_list_head = QHBoxLayout()
        sub_list_head.setSpacing(8)
        lbl_list_title = QLabel("📝 实时字幕对白列表", self)
        lbl_list_title.setStyleSheet("font-size: 13.5px; font-weight: 700; color: #18181B; border: none; background: transparent;")
        sub_list_head.addWidget(lbl_list_title)

        self.lbl_sub_list_badge = QLabel("共 0 句", self)
        self.lbl_sub_list_badge.setStyleSheet("font-size: 10.5px; font-weight: 600; color: #7C3AED; background-color: #F5F3FF; border: 1px solid #DDD6FE; border-radius: 5px; padding: 2px 8px;")
        sub_list_head.addWidget(self.lbl_sub_list_badge)

        self.edit_sub_search = QLineEdit(self)
        self.edit_sub_search.setObjectName("SubSearchInput")
        self.edit_sub_search.setPlaceholderText("🔍 搜索台词或时间点...")
        self.edit_sub_search.setClearButtonEnabled(True)
        self.edit_sub_search.setFixedHeight(28)
        self.edit_sub_search.setMinimumWidth(160)
        self.edit_sub_search.setMaximumWidth(240)
        self.edit_sub_search.setStyleSheet("""
            QLineEdit#SubSearchInput {
                background-color: #F8FAFC;
                border: 1px solid #E4E4E7;
                border-radius: 7px;
                padding: 3px 10px;
                color: #18181B;
                font-size: 11.5px;
            }
            QLineEdit#SubSearchInput:focus {
                border: 1.5px solid #8B5CF6;
                background-color: #FFFFFF;
            }
        """)
        self.edit_sub_search.textChanged.connect(self.filter_items)
        sub_list_head.addWidget(self.edit_sub_search, 1)

        sub_list_head.addStretch()

        lbl_list_hint = QLabel("💡 单击跳转 · 双击微调台词/时间轴", self)
        lbl_list_hint.setStyleSheet("font-size: 11px; color: #71717A; border: none; background: transparent;")
        sub_list_head.addWidget(lbl_list_hint)

        self.btn_add_sub = QPushButton("➕ 新增", self)
        self.btn_add_sub.setCursor(Qt.PointingHandCursor)
        self.btn_add_sub.setFixedHeight(26)
        self.btn_add_sub.setToolTip("在当前选中行下方或当前播放时间插入新字幕行")
        self.btn_add_sub.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #E4E4E7;
                border-radius: 6px;
                padding: 2px 8px;
                font-size: 11px;
                font-weight: 600;
                color: #52525B;
            }
            QPushButton:hover {
                background-color: #F5F3FF;
                border-color: #C4B5FD;
                color: #6D28D9;
            }
            QPushButton:disabled {
                color: #D4D4D8;
                background-color: #FAFAFA;
            }
        """)
        self.btn_add_sub.setEnabled(False)
        self.btn_add_sub.clicked.connect(self._on_add_btn_clicked)
        sub_list_head.addWidget(self.btn_add_sub)

        self.btn_save_sub = QPushButton("💾 保存字幕", self)
        self.btn_save_sub.setCursor(Qt.PointingHandCursor)
        self.btn_save_sub.setFixedHeight(26)
        self.btn_save_sub.setToolTip("将修改后的台词与时间轴回写保存至当前字幕文件 (Ctrl+S)")
        self.btn_save_sub.setEnabled(False)
        self._update_save_btn_style(False)
        self.btn_save_sub.clicked.connect(lambda: self.sig_save_requested.emit())
        sub_list_head.addWidget(self.btn_save_sub)

        card_sub_layout.addLayout(sub_list_head)

        self.lbl_sub_list_empty = QLabel("💬 暂无字幕文件\n\n请在上方选择或匹配字幕文件，载入后将在此列出完整台词\n随视频播放实时高亮跟随，单击任意句子直达该片段，双击可在线微调台词与时间轴。", self)
        self.lbl_sub_list_empty.setAlignment(Qt.AlignCenter)
        self.lbl_sub_list_empty.setStyleSheet("color: #A1A1AA; font-size: 12px; background-color: #FAFAFB; border: 1.5px dashed #E4E4E7; border-radius: 12px; padding: 24px;")
        card_sub_layout.addWidget(self.lbl_sub_list_empty, 1)

        self.list_subtitles = QListWidget(self)
        self.list_subtitles.setObjectName("sub_list_widget")
        self.list_subtitles.setSelectionMode(QAbstractItemView.SingleSelection)
        self.list_subtitles.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list_subtitles.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list_subtitles.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_subtitles.setStyleSheet("""
            QListWidget { background-color: #FAFAFB; border: 1px solid #E4E4E7; border-radius: 12px; outline: none; padding: 4px; }
            QListWidget::item { border-radius: 8px; margin: 2px 2px; padding: 0px; background-color: transparent; }
            QListWidget::item:hover { background-color: #F5F3FF; }
            QListWidget::item:selected { background-color: #EDE9FE; border: 1.5px solid #A78BFA; }
        """)
        self.list_subtitles.itemClicked.connect(self._on_item_clicked)
        self.list_subtitles.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.list_subtitles.customContextMenuRequested.connect(self._on_context_menu)
        self.list_subtitles.hide()
        card_sub_layout.addWidget(self.list_subtitles, 1)

    def _update_save_btn_style(self, dirty: bool):
        self._has_unsaved_changes = dirty
        if dirty:
            self.btn_save_sub.setText("💾 保存修改 *")
            self.btn_save_sub.setStyleSheet("""
                QPushButton {
                    background-color: #8B5CF6;
                    border: 1px solid #7C3AED;
                    border-radius: 6px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: 700;
                    color: #FFFFFF;
                }
                QPushButton:hover {
                    background-color: #7C3AED;
                }
            """)
        else:
            self.btn_save_sub.setText("💾 保存字幕")
            self.btn_save_sub.setStyleSheet("""
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #E4E4E7;
                    border-radius: 6px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: 600;
                    color: #52525B;
                }
                QPushButton:hover {
                    background-color: #F5F3FF;
                    border-color: #C4B5FD;
                    color: #6D28D9;
                }
                QPushButton:disabled {
                    color: #D4D4D8;
                    background-color: #FAFAFA;
                }
            """)

    def mark_saved(self):
        """标记当前字幕修改已保存"""
        self._update_save_btn_style(False)

    def mark_dirty(self):
        """标记当前存在未保存的字幕微调"""
        self.btn_save_sub.setEnabled(True)
        self._update_save_btn_style(True)

    def _on_item_clicked(self, item: QListWidgetItem):
        sub_data = item.data(Qt.UserRole)
        if sub_data and isinstance(sub_data, dict):
            self.sig_item_clicked.emit(sub_data)

    def _on_item_double_clicked(self, item: QListWidgetItem):
        row = self.list_subtitles.row(item)
        if row >= 0:
            self.open_edit_dialog_for_row(row)

    def _on_add_btn_clicked(self):
        row = self.list_subtitles.currentRow()
        self.sig_add_requested.emit(row)

    def _on_context_menu(self, pos):
        item = self.list_subtitles.itemAt(pos)
        row = self.list_subtitles.row(item) if item else self.list_subtitles.currentRow()

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E4E4E7;
                border-radius: 8px;
                padding: 4px;
                color: #18181B;
                font-size: 12px;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: #F5F3FF;
                color: #6D28D9;
            }
            QMenu::separator {
                height: 1px;
                background: #E4E4E7;
                margin: 4px 6px;
            }
        """)

        act_edit = menu.addAction("✏️ 微调该句台词与时间轴 (双击)")
        act_edit.setEnabled(row >= 0)
        act_add = menu.addAction("➕ 在下方插入新字幕行")
        act_del = menu.addAction("🗑️ 删除该句字幕")
        act_del.setEnabled(row >= 0)
        menu.addSeparator()
        act_save = menu.addAction("💾 立即保存字幕文件 (Ctrl+S)")
        act_save.setEnabled(self.btn_save_sub.isEnabled())

        chosen = menu.exec(QCursor.pos())
        if chosen == act_edit and row >= 0:
            self.open_edit_dialog_for_row(row)
        elif chosen == act_add:
            self.sig_add_requested.emit(row)
        elif chosen == act_del and row >= 0:
            self.sig_delete_requested.emit(row)
        elif chosen == act_save:
            self.sig_save_requested.emit()

    def open_edit_dialog_for_row(self, row: int) -> bool:
        """弹出指定行字幕的在线微调窗口"""
        if row < 0 or row >= len(self._items_ref):
            return False
        sub_data = self._items_ref[row]
        dlg = SubtitleEditDialog(sub_data, index=row, parent=self)
        if dlg.exec() == QDialog.Accepted:
            self.edit_subtitle_at(
                row,
                new_text=dlg.sub_data["text"],
                start_ms=dlg.sub_data["start_ms"],
                end_ms=dlg.sub_data["end_ms"],
                start_str=dlg.sub_data["start_str"],
                end_str=dlg.sub_data["end_str"],
            )
            return True
        return False

    def edit_subtitle_at(
        self,
        row: int,
        new_text: Optional[str] = None,
        start_ms: Optional[int] = None,
        end_ms: Optional[int] = None,
        start_str: Optional[str] = None,
        end_str: Optional[str] = None,
    ) -> bool:
        """以编程或弹窗方式原地更新指定行字幕并触发视图刷新"""
        if row < 0 or row >= len(self._items_ref):
            return False
        target = self._items_ref[row]
        fmt = "srt" if "," in str(target.get("start_str", "")) else "ass"
        if start_ms is not None:
            target["start_ms"] = int(start_ms)
            target["start_str"] = start_str or format_timestamp(start_ms / 1000.0, fmt)
        if end_ms is not None:
            target["end_ms"] = int(end_ms)
            target["end_str"] = end_str or format_timestamp(end_ms / 1000.0, fmt)
        if new_text is not None:
            target["text"] = str(new_text).strip()

        self.mark_dirty()
        self.sig_subtitles_modified.emit()
        return True

    def populate_items(self, items: List[Dict[str, Any]], keep_dirty: bool = False):
        """填充字幕条目列表"""
        self._items_ref = items if isinstance(items, list) else []
        self.list_subtitles.clear()
        if not keep_dirty:
            self._update_save_btn_style(False)

        if not self._items_ref:
            self.list_subtitles.hide()
            self.lbl_sub_list_empty.show()
            self.lbl_sub_list_badge.setText("共 0 句")
            self.btn_add_sub.setEnabled(False)
            self.btn_save_sub.setEnabled(False)
            return

        self.lbl_sub_list_empty.hide()
        self.list_subtitles.show()
        self.btn_add_sub.setEnabled(True)
        self.btn_save_sub.setEnabled(True)
        self.lbl_sub_list_badge.setText(f"共 {len(self._items_ref)} 句")

        for idx, s in enumerate(self._items_ref):
            item = QListWidgetItem()
            card = QFrame()
            card.setStyleSheet("background: transparent; border: none; padding: 4px 6px;")
            c_layout = QHBoxLayout(card)
            c_layout.setContentsMargins(6, 4, 6, 4)
            c_layout.setSpacing(8)

            lbl_idx = QLabel(f"#{idx + 1}")
            lbl_idx.setStyleSheet("color: #A1A1AA; font-size: 10.5px; font-weight: 600; width: 32px;")
            c_layout.addWidget(lbl_idx)

            time_badge = QLabel(f"{s['start_str']} → {s['end_str']}")
            time_badge.setStyleSheet("color: #7C3AED; background: #F5F3FF; border: 1px solid #DDD6FE; border-radius: 4px; padding: 1px 5px; font-size: 10.5px; font-family: monospace; font-weight: 600;")
            c_layout.addWidget(time_badge)

            lbl_txt = QLabel(s["text"])
            lbl_txt.setStyleSheet("color: #18181B; font-size: 12px; font-weight: 500;")
            lbl_txt.setWordWrap(True)
            c_layout.addWidget(lbl_txt, 1)

            card._lbl_idx = lbl_idx
            card._time_badge = time_badge
            card._lbl_txt = lbl_txt

            item.setSizeHint(card.sizeHint())
            item.setData(Qt.UserRole, s)
            self.list_subtitles.addItem(item)
            self.list_subtitles.setItemWidget(item, card)

        # 若搜索框有过滤词，保持过滤状态
        if self.edit_sub_search.text().strip():
            self.filter_items(self.edit_sub_search.text())

    def refresh_items_in_place(self, items: List[Dict[str, Any]], keep_dirty: bool = True) -> bool:
        """当字幕条目数量未变时原地增量更新各行标签与数据，避免全表销毁重建导致的闪烁"""
        if not isinstance(items, list) or len(items) == 0 or len(items) != self.list_subtitles.count():
            self.populate_items(items, keep_dirty=keep_dirty)
            return False

        self._items_ref = items
        if not keep_dirty:
            self._update_save_btn_style(False)

        for idx, s in enumerate(self._items_ref):
            item = self.list_subtitles.item(idx)
            if item is None:
                continue
            item.setData(Qt.UserRole, s)
            card = self.list_subtitles.itemWidget(item)
            if card is not None and hasattr(card, "_lbl_idx"):
                card._lbl_idx.setText(f"#{idx + 1}")
                card._time_badge.setText(f"{s['start_str']} → {s['end_str']}")
                card._lbl_txt.setText(s["text"])
                item.setSizeHint(card.sizeHint())

        if self.edit_sub_search.text().strip():
            self.filter_items(self.edit_sub_search.text())
        else:
            self.lbl_sub_list_badge.setText(f"共 {len(self._items_ref)} 句")
        return True

    def filter_items(self, query: str):
        """根据关键词实时过滤字幕列表"""
        q = str(query or "").strip().lower()
        total = self.list_subtitles.count()
        if total == 0:
            return
        visible_cnt = 0
        for i in range(total):
            item = self.list_subtitles.item(i)
            sub_data = item.data(Qt.UserRole) or {}
            if not q:
                item.setHidden(False)
                visible_cnt += 1
            else:
                haystack = f"{sub_data.get('text', '')} {sub_data.get('start_str', '')} {sub_data.get('end_str', '')}".lower()
                matched = q in haystack
                item.setHidden(not matched)
                if matched:
                    visible_cnt += 1

        if q:
            self.lbl_sub_list_badge.setText(f"筛选 {visible_cnt}/{total} 句")
        else:
            self.lbl_sub_list_badge.setText(f"共 {total} 句")

    def highlight_item(self, found_idx: int):
        """高亮并平滑居中滚动至指定序号条目"""
        if 0 <= found_idx < self.list_subtitles.count():
            if self.list_subtitles.currentRow() != found_idx:
                self.list_subtitles.blockSignals(True)
                self.list_subtitles.setCurrentRow(found_idx)
                cur_item = self.list_subtitles.item(found_idx)
                if cur_item and not cur_item.isHidden():
                    self.list_subtitles.scrollToItem(cur_item, QAbstractItemView.PositionAtCenter)
                self.list_subtitles.blockSignals(False)

    def clear_selection(self):
        """清除高亮选中项"""
        if self.list_subtitles.currentRow() != -1:
            self.list_subtitles.blockSignals(True)
            self.list_subtitles.clearSelection()
            self.list_subtitles.setCurrentRow(-1)
            self.list_subtitles.blockSignals(False)


__all__ = [
    "SubtitleEditDialog",
    "BurnerSubListCard",
]

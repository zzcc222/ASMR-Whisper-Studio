# -*- coding: utf-8 -*-
"""
ASMR Whisper Studio - 字幕压制任务执行与批量队列接力调度控制器 (ui.controllers.burner_runner)
负责 SubBurnerWorker 后台压制进程启停、进度统计、批量队列自动接续以及系统托盘/礼花弹窗通知
(与 ui.controllers.transcribe_runner 对称设计，实现视图层与控制层彻底解耦)
"""

import os
import time
from typing import Optional

from PySide6.QtCore import QObject, Slot, QTimer
from PySide6.QtWidgets import QMessageBox, QSystemTrayIcon

from core.media.sub_burner import SubBurnerConfig
from ui.workers.burner_worker import SubBurnerWorker
from ui.widgets import ConfettiOverlay


class BurnerRunner(QObject):
    """字幕压制执行与批量任务接力控制器"""

    def __init__(self, queue_panel):
        super().__init__(queue_panel)
        self.panel = queue_panel
        self.worker: Optional[SubBurnerWorker] = None
        self.start_timestamp: float = 0.0

    @property
    def tab(self):
        return self.panel.tab

    def start_burn(self):
        """校验参数并启动 FFmpeg 字幕压制或软字幕封装"""
        video_p = self.panel.edit_video_path.text().strip()
        sub_p = self.panel.edit_sub_path.text().strip()

        if not video_p or not os.path.exists(video_p):
            QMessageBox.warning(self.tab, "提示", "请先选择有效的音视频源文件！")
            return
        if not sub_p or not os.path.exists(sub_p):
            QMessageBox.warning(self.tab, "提示", "请先选择有效的字幕文件 (ASS / SRT)！")
            return

        # 若当前字幕存在在线微调未保存内容，压制前自动回写保存
        if self.tab and hasattr(self.tab, "player_panel"):
            sub_card = getattr(self.tab.player_panel, "sub_list_card", None)
            if sub_card and getattr(sub_card, "_has_unsaved_changes", False):
                self.tab.player_panel.save_current_subtitles()

        out_dir = self.panel.edit_output_dir.text().strip()
        if not out_dir:
            out_dir = os.path.dirname(os.path.abspath(video_p))

        base_name = os.path.splitext(os.path.basename(video_p))[0]
        style = self.tab.style_panel
        is_hard = style.radio_hard.isChecked()
        media_info = self.tab.player_panel.media_info
        is_pure_audio = not media_info.get("is_video", False)
        ext = ".mkv" if "mkv" in style.combo_container.currentText().lower() else ".mp4"
        if not is_hard and is_pure_audio and ext == ".mp4":
            ext = ".mkv"

        suffix = "_softsub" if not is_hard else "_hardsub"
        output_file = os.path.join(out_dir, f"{base_name}{suffix}{ext}")

        counter = 1
        while os.path.exists(output_file):
            output_file = os.path.join(out_dir, f"{base_name}{suffix}_{counter}{ext}")
            counter += 1

        mode_str = "hard" if is_hard else "soft"
        encoder_str = style.combo_encoder.currentData() or "h264_nvenc"
        cq_val = style.combo_quality.currentData() or 23
        sub_style = style.get_subtitle_style() if hasattr(style, "get_subtitle_style") else {}

        config = SubBurnerConfig(
            input_video=video_p,
            input_subtitle=sub_p,
            output_file=output_file,
            mode=mode_str,
            encoder=encoder_str,
            cq_value=cq_val,
            overwrite=True,
            use_custom_style=bool(is_hard and sub_style),
            font_family=sub_style.get("font_family", "Yu Gothic UI"),
            font_size=int(sub_style.get("font_size", 54)),
            sub_align=int(sub_style.get("align", 2)),
            sub_margin_v=int(sub_style.get("margin_v", 45)),
            sub_color_hex=sub_style.get("color_hex", "#FFFFFF"),
            sub_outline_hex=sub_style.get("outline_hex", "#000000"),
            sub_outline_width=float(sub_style.get("outline_width", 2.5)),
        )

        total_dur = media_info.get("duration", 0.0)

        if self.panel._batch_completed == 0:
            self.panel.txt_log.clear()
        self.panel.prog_bar.setValue(0)
        self.panel.lbl_status.setText("正在执行...")
        self.panel.lbl_stats.setText("耗时: 00:00 | 帧率: -- | 倍速: --")
        self.start_timestamp = time.time()

        self.worker = SubBurnerWorker(config=config, total_duration=total_dur)
        self.worker.sig_started.connect(self._on_worker_started)
        self.worker.sig_progress.connect(self._on_worker_progress)
        self.worker.sig_log.connect(self._on_worker_log)
        self.worker.sig_finished.connect(self._on_worker_finished)

        self.tab.pause_player()
        self.panel.set_locked(True)
        self.panel.btn_start.setEnabled(False)
        self.panel.btn_stop.setEnabled(True)

        try:
            self.worker.start()
        except Exception as e:
            self.panel.set_locked(False)
            self.panel.btn_start.setEnabled(True)
            self.panel.btn_stop.setEnabled(False)
            self.panel.txt_log.append(f"❌ 启动压制任务失败: {e}")

    def stop_burn(self):
        """中止压制任务并清空后续等待队列"""
        if self.panel.batch_queue:
            self.panel.batch_queue.clear()
            self.panel._update_batch_ui()
        if self.worker and self.worker.isRunning():
            self.panel.lbl_status.setText("正在取消...")
            self.worker.stop()
            self.panel.btn_stop.setEnabled(False)

    @Slot()
    def _on_worker_started(self):
        self.panel.lbl_status.setText("压制进行中...")
        self.panel.txt_log.append("🚀 FFmpeg 压制流水线已启动...")
        if hasattr(self.tab, "update_tray_status"):
            self.tab.update_tray_status("压制中", "burning")

    @Slot(float, str, str, str)
    def _on_worker_progress(self, progress: float, time_str: str, speed_str: str, fps_str: str):
        self.panel.prog_bar.setValue(int(progress))
        elapsed = (time.time() - self.start_timestamp) if self.start_timestamp > 0 else 0.0
        m = int(elapsed // 60)
        s = int(elapsed % 60)
        self.panel.lbl_status.setText(f"压制中: {progress:.1f}%")
        self.panel.lbl_stats.setText(f"耗时: {m:02d}:{s:02d} | 进度时间: {time_str} | 帧率: {fps_str} | 倍速: {speed_str}")
        if hasattr(self.tab, "update_tray_status"):
            self.tab.update_tray_status(f"压制 {progress:.0f}%", "burning")

    @Slot(str)
    def _on_worker_log(self, msg: str):
        self.panel.txt_log.append(msg)

    @Slot(bool, str, str)
    def _on_worker_finished(self, success: bool, output_file: str, message: str):
        self.panel.set_locked(False)
        self.panel.btn_start.setEnabled(True)
        self.panel.btn_stop.setEnabled(False)
        elapsed = (time.time() - self.start_timestamp) if self.start_timestamp > 0 else 0.0
        m = int(elapsed // 60)
        s = int(elapsed % 60)

        if hasattr(self.tab, "update_tray_status"):
            self.tab.update_tray_status("待命就绪", "idle")

        win = getattr(self.tab, "win", None) if self.tab else None
        if not win and self.tab and hasattr(self.tab, "parent"):
            win = self.tab.parent()
        is_win_visible = (
            win.isVisible()
            if (win and hasattr(win, "isVisible"))
            else (self.tab.isVisible() if (self.tab and hasattr(self.tab, "isVisible")) else False)
        )
        dialog_parent = self.tab if self.tab else win

        if success:
            self.panel.prog_bar.setValue(100)
            self.panel.lbl_status.setText("压制成功完成！")
            self.panel.lbl_stats.setText(f"总耗时: {m:02d}:{s:02d}")
            self.panel.txt_log.append(f"🎉 任务完成: {message}")

            # 若批量队列中仍有后续待压制任务，自动接续下一项
            if self.panel.batch_queue:
                self.panel._batch_completed += 1
                next_task = self.panel.batch_queue.pop(0)
                self.panel._update_batch_ui()
                self.panel.edit_video_path.setText(next_task["video"])
                if next_task.get("sub"):
                    self.panel.edit_sub_path.setText(next_task["sub"])
                self.panel.txt_log.append(
                    f"⏭️ [批量队列] 自动接续下一项 ({self.panel._batch_completed + 1}/{self.panel._batch_total}): "
                    f"{os.path.basename(next_task['video'])}"
                )
                QTimer.singleShot(250, self.start_burn)
                return

            total_done = self.panel._batch_completed + 1
            self.panel._batch_completed = 0
            self.panel._batch_total = 0
            self.panel._update_batch_ui()

            if is_win_visible and dialog_parent:
                ConfettiOverlay.launch(dialog_parent)
                if total_done > 1:
                    QMessageBox.information(
                        dialog_parent,
                        "批量压制完成",
                        f"🎉 批量字幕压制全部完成 (共 {total_done} 个视频)！\n\n最后一项耗时: {m:02d}:{s:02d}\n最新输出文件:\n{output_file}",
                    )
                else:
                    QMessageBox.information(
                        dialog_parent,
                        "压制完成",
                        f"🎉 字幕压制完成！\n\n总耗时: {m:02d}:{s:02d}\n文件已保存至:\n{output_file}",
                    )
            else:
                if win and hasattr(win, "tray_manager") and win.tray_manager:
                    win.tray_manager.show_notification("压制完成", f"🎉 字幕压制完成！总耗时: {m:02d}:{s:02d}\n文件已保存至成片目录。")
        else:
            self.panel._batch_completed = 0
            self.panel._batch_total = 0
            self.panel._update_batch_ui()
            if "取消" in message or "cancel" in message.lower() or "abort" in message.lower() or "stop" in message.lower():
                self.panel.lbl_status.setText("压制已取消")
                self.panel.txt_log.append(f"⚠️ 压制任务已取消: {message}")
                if is_win_visible and dialog_parent:
                    QMessageBox.information(dialog_parent, "已取消", "压制任务已成功终止。")
            else:
                self.panel.lbl_status.setText("压制失败")
                self.panel.txt_log.append(f"❌ 压制未成功完成: {message}")
                if is_win_visible and dialog_parent:
                    QMessageBox.critical(dialog_parent, "压制失败", f"压制任务执行失败:\n{message}")
                else:
                    if win and hasattr(win, "tray_manager") and win.tray_manager:
                        win.tray_manager.show_notification("压制失败", f"❌ 压制未成功完成: {message}", QSystemTrayIcon.Warning)

    def shutdown(self):
        if self.worker and self.worker.isRunning():
            try:
                self.worker.stop()
                self.worker.wait(800)
            except Exception:
                pass


__all__ = [
    "BurnerRunner",
]
